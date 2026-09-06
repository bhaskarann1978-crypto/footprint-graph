import sys
import json
import os
import random
import pandas as pd
import requests
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                             QHBoxLayout, QWidget, QPushButton, QMessageBox, 
                             QLineEdit, QFormLayout, QTabWidget, QListWidget, 
                             QDialog, QListWidgetItem, QProgressBar, QComboBox,
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QBrush
from api.angel_login import AngelOneManager

try:
    from SmartApi.smartWebSocketV2 import SmartWebSocketV2
except ImportError:
    SmartWebSocketV2 = None


class SymbolLoaderThread(QThread):
    loaded_signal = pyqtSignal(list)

    def run(self):
        symbols_list = []
        seen = set()
        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                data = response.json()
                for item in data:
                    symbol = item.get('symbol', '')
                    exch_seg = item.get('exch_seg', '')
                    if exch_seg in ["NSE", "BSE"] and symbol:
                        clean_sym = symbol.replace("-EQ", "").strip()
                        if clean_sym:
                            identifier = (clean_sym, exch_seg)
                            if identifier not in seen:
                                seen.add(identifier)
                                symbols_list.append((clean_sym, exch_seg))
            else:
                symbols_list = [("NIFTY", "NSE"), ("RELIANCE", "NSE"), ("TCS", "NSE")]
        except Exception:
            symbols_list = [("NIFTY", "NSE"), ("RELIANCE", "NSE"), ("TCS", "NSE")]
            
        self.loaded_signal.emit(symbols_list)


class SymbolSearchDialog(QDialog):
    def __init__(self, symbols_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Search & Select Market Symbols (NSE/BSE)")
        self.setGeometry(200, 200, 450, 550)
        self.selected_symbol = None
        self.symbols_list = symbols_list
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to filter (e.g. NIFTY, RELIANCE)...")
        self.search_input.textChanged.connect(self.filter_symbols)
        self.search_input.setStyleSheet("padding: 8px; font-size: 14px; background: #222; color: #fff;")
        layout.addWidget(self.search_input)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("background-color: #1e1e1e; color: #00bcd4; font-weight: bold; font-size: 14px;")
        self.list_widget.itemDoubleClicked.connect(self.accept_symbol)
        layout.addWidget(self.list_widget)
        
        self.populate_list(self.symbols_list)
        
        btn_layout = QHBoxLayout()
        self.add_fav_btn = QPushButton("⭐ Add to Watchlist")
        self.add_fav_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 8px;")
        self.add_fav_btn.clicked.connect(lambda: self.accept_symbol(self.list_widget.currentItem()))
        
        close_btn = QPushButton("Cancel")
        close_btn.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 8px;")
        close_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.add_fav_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def populate_list(self, data):
        self.list_widget.clear()
        for sym, segment in data:
            item = QListWidgetItem(f"📌 {sym}  [{segment}]")
            item.setData(Qt.UserRole, f"{sym} [{segment}]")
            self.list_widget.addItem(item)

    def filter_symbols(self, text):
        query = text.strip().upper()
        filtered = [(sym, seg) for sym, seg in self.symbols_list if query in sym]
        self.populate_list(filtered)

    def accept_symbol(self, item):
        if item:
            self.selected_symbol = item.data(Qt.UserRole)
            self.accept()
        else:
            QMessageBox.warning(self, "Warning", "Please select a symbol first!")


class FootprintApp(QMainWindow):
    def __init__(self, master_symbols):
        super().__init__()
        self.setWindowTitle("🚀 Pro Multi-Candle Graphical Footprint Terminal")
        self.setGeometry(100, 100, 1450, 900)
        
        self.watchlist_file = "watchlist.json"
        self.master_symbols = master_symbols
        self.api_manager = None
        self.current_symbol = "NIFTY [NSE]"
        
        self.init_ui()
        self.load_watchlist()

        # Timer for live simulation feed update
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_footprint_grid)
        self.timer.start(1200)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # ==================== LEFT PANEL ====================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        title_label = QLabel("🔑 Angel One Credentials")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #fff;")
        left_layout.addWidget(title_label)
        
        form_layout = QFormLayout()
        self.api_key_input = QLineEdit()
        self.client_id_input = QLineEdit("CHNA2500")
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.totp_input = QLineEdit()
        self.totp_input.setEchoMode(QLineEdit.Password)
        
        for field, lbl in [(self.api_key_input, "API Key:"), (self.client_id_input, "Client ID:"), 
                           (self.pin_input, "PIN:"), (self.totp_input, "OTP:")]:
            field.setStyleSheet("background: #222; color: #fff; padding: 4px;")
            form_layout.addRow(lbl, field)
            
        left_layout.addLayout(form_layout)
        
        self.login_btn = QPushButton("Login to Live Market")
        self.login_btn.setStyleSheet("background-color: #007ACC; color: white; font-weight: bold; padding: 6px;")
        self.login_btn.clicked.connect(self.execute_login)
        left_layout.addWidget(self.login_btn)
        
        self.status_label = QLabel("🔴 Status: Offline (Simulation Mode)")
        self.status_label.setStyleSheet("font-weight: bold; color: orange;")
        left_layout.addWidget(self.status_label)
        
        watchlist_title = QLabel("📊 Watchlist Tabs")
        watchlist_title.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px; color: #fff;")
        left_layout.addWidget(watchlist_title)
        
        cat_layout = QHBoxLayout()
        self.cat_input = QLineEdit()
        self.cat_input.setPlaceholderText("Tab Name...")
        self.cat_input.setStyleSheet("background: #222; color: #fff;")
        self.add_cat_btn = QPushButton("+ Tab")
        self.add_cat_btn.clicked.connect(self.add_category_tab)
        cat_layout.addWidget(self.cat_input)
        cat_layout.addWidget(self.add_cat_btn)
        left_layout.addLayout(cat_layout)
        
        self.open_picker_btn = QPushButton("🔍 Open Symbol Finder (+ Add)")
        self.open_picker_btn.setStyleSheet("background-color: #17a2b8; color: white; font-weight: bold; padding: 6px;")
        self.open_picker_btn.clicked.connect(self.open_symbol_picker)
        left_layout.addWidget(self.open_picker_btn)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(lambda idx: self.tab_widget.removeTab(idx))
        left_layout.addWidget(self.tab_widget)
        
        self.delete_symbol_btn = QPushButton("🗑️ Delete Selected Symbol")
        self.delete_symbol_btn.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 6px;")
        self.delete_symbol_btn.clicked.connect(self.delete_selected_symbol)
        left_layout.addWidget(self.delete_symbol_btn)
        
        load_bhav_btn = QPushButton("📂 Load Offline Bhavcopy CSV")
        load_bhav_btn.setStyleSheet("background-color: #6c757d; color: white; font-weight: bold; padding: 6px;")
        load_bhav_btn.clicked.connect(self.load_bhavcopy_offline)
        left_layout.addWidget(load_bhav_btn)
        
        main_layout.addWidget(left_widget, 1)
        
        # ==================== RIGHT PANEL ====================
        right_panel = QVBoxLayout()
        
        # Top Header Bar with Symbol Info & Timeframe Selector
        top_bar_layout = QHBoxLayout()
        self.header_info_label = QLabel(f"📈 Active Symbol: {self.current_symbol} | Multi-Candle Order Flow Footprint")
        self.header_info_label.setStyleSheet("background-color: #111; color: #00bcd4; font-weight: bold; font-size: 14px; padding: 8px;")
        top_bar_layout.addWidget(self.header_info_label, 4)
        
        tf_label = QLabel("⏱️ TF:")
        tf_label.setStyleSheet("font-weight: bold; color: #00ffcc;")
        top_bar_layout.addWidget(tf_label)
        
        self.tf_combo = QComboBox()
        self.tf_combo.addItems(["1M", "3M", "5M", "15M", "30M", "1H"])
        self.tf_combo.setStyleSheet("background-color: #222; color: #00ffcc; font-weight: bold; padding: 4px;")
        self.tf_combo.currentIndexChanged.connect(self.update_footprint_grid)
        top_bar_layout.addWidget(self.tf_combo, 1)
        
        right_panel.addLayout(top_bar_layout)
        
        # Multi-Candle Footprint Grid Table (Columns: Price Level, Candle 1, Candle 2, Candle 3 (Current))
        self.footprint_grid = QTableWidget()
        self.footprint_grid.setColumnCount(4)
        self.footprint_grid.setHorizontalHeaderLabels([
            "Price Level (₹)", 
            "Candle 1 [10:00] (Sell x Buy)", 
            "Candle 2 [10:05] (Sell x Buy)", 
            "Candle 3 [10:10] (Current) (Sell x Buy)"
        ])
        self.footprint_grid.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.footprint_grid.setStyleSheet("""
            QTableWidget {
                background-color: #121212;
                color: #ffffff;
                gridline-color: #333333;
                font-family: Consolas;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #1f1f1f;
                color: #00bcd4;
                font-weight: bold;
                border: 1px solid #333;
                padding: 6px;
            }
        """)
        right_panel.addWidget(self.footprint_grid)
        
        main_layout.addLayout(right_panel, 3)

    def update_footprint_grid(self):
        """Populates multi-candle grid with Bid x Ask split columns and footer metrics rows"""
        p = random.randint(24440, 24460)
        
        # Row data structure: (Price, Candle 1 Text, Candle 2 Text, Candle 3 Text, Row Type)
        matrix_rows = [
            (f"{p+4}.00", "650 x 3380  🟢", "120 x 450   🟢", "450 x 1200  🟢", "normal"),
            (f"{p+3}.00", "2210 x 1170 🟥", "300 x 280   ⚪", "890 x 920   ⚪", "normal"),
            (f"{p+2}.00", "780 x 390   🟥", "650 x 150   🟥", "1420 x 2150 🔥", "poc"),
            (f"{p+1}.00", "--- x ---     ", "890 x 920   ⚪", "410 x 190   🟥", "normal"),
            (f"{p}.00",   "--- x ---     ", "1420 x 2150 🟢", "90 x 540    🟢", "normal"),
            ("-------------------------------------------------------------------------------------------------", "--------------------", "--------------------", "--------------------", "divider"),
            ("TOTAL SELL", "3.7K", "1.8K", "3.2K", "footer_sell"),
            ("TOTAL BUY",  "8.2K", "4.5K", "4.9K", "footer_buy"),
            ("DELTA (Δ)",  "+4.5K 🟢", "+2.7K 🟢", "+1.7K 🟢", "footer_delta"),
            ("CUMULATIVE Δ", "+12.9K", "+15.6K", "+17.3K (Bullish)", "footer_cum")
        ]
        
        self.footprint_grid.setRowCount(len(matrix_rows))
        
        for row_idx, data in enumerate(matrix_rows):
            price, c1, c2, c3, row_type = data
            items = [
                QTableWidgetItem(price),
                QTableWidgetItem(c1),
                QTableWidgetItem(c2),
                QTableWidgetItem(c3)
            ]
            
            # Color coding rows based on order flow type
            for col_idx, item in enumerate(items):
                item.setTextAlignment(Qt.AlignCenter)
                if row_type == "poc":
                    item.setBackground(QBrush(QColor(0, 100, 100)))
                    item.setForeground(QBrush(QColor(255, 255, 255)))
                elif row_type == "footer_sell":
                    item.setBackground(QBrush(QColor(60, 20, 20)))
                    item.setForeground(QBrush(QColor(255, 100, 100)))
                elif row_type == "footer_buy":
                    item.setBackground(QBrush(QColor(20, 60, 20)))
                    item.setForeground(QBrush(QColor(100, 255, 100)))
                elif row_type in ["footer_delta", "footer_cum"]:
                    item.setBackground(QBrush(QColor(30, 30, 50)))
                    item.setForeground(QBrush(QColor(0, 255, 204)))
                elif row_type == "divider":
                    item.setBackground(QBrush(QColor(40, 40, 40)))
                else:
                    item.setBackground(QBrush(QColor(18, 18, 18)))
                    
                self.footprint_grid.setItem(row_idx, col_idx, item)

    def load_bhavcopy_offline(self):
        folder_path = "data/PR040926"
        csv_path = None
        if os.path.exists(folder_path):
            for file in os.listdir(folder_path):
                if file.endswith(".csv"):
                    csv_path = os.path.join(folder_path, file)
                    break
        
        if csv_path and os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                sym_clean = self.current_symbol.split()[0]
                row = df[df['SYMBOL'].str.strip() == sym_clean]
                if not row.empty:
                    op, hi, lo, cl = row.iloc[0]['OPEN'], row.iloc[0]['HIGH'], row.iloc[0]['LOW'], row.iloc[0]['CLOSE']
                    vol = row.iloc[0].get('TOTTRDQTY', row.iloc[0].get('TTL_TRD_QNT', 0))
                    self.header_info_label.setText(f"📂 Bhavcopy Loaded [{sym_clean}] | O:{op} H:{hi} L:{lo} C:{cl} Vol:{vol}")
                    QMessageBox.information(self, "Success", f"Successfully loaded Bhavcopy for {sym_clean}!")
                else:
                    QMessageBox.warning(self, "Not Found", f"Symbol '{sym_clean}' not found in CSV.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to read CSV: {e}")
        else:
            QMessageBox.warning(self, "Missing Folder", "No CSV file found inside 'data/PR040926' folder!")

    def delete_selected_symbol(self):
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, QListWidget):
            selected_items = current_tab.selectedItems()
            if selected_items:
                for item in selected_items:
                    current_tab.takeItem(current_tab.row(item))
                self.save_watchlist()
            else:
                QMessageBox.warning(self, "Warning", "Please select a symbol to delete!")
        else:
            QMessageBox.warning(self, "Warning", "No active watchlist tab found!")

    def execute_login(self):
        api_key = self.api_key_input.text().strip()
        client_id = self.client_id_input.text().strip()
        pin = self.pin_input.text().strip()
        totp = self.totp_input.text().strip()
        
        if not all([api_key, client_id, pin, totp]):
            QMessageBox.warning(self, "Warning", "Please fill in all credentials!")
            return
            
        try:
            self.api_manager = AngelOneManager(api_key, client_id, pin, totp)
            success, msg = self.api_manager.login()
            self.status_label.setText(msg)
            if success:
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                self.header_info_label.setText(f"📈 Active Symbol: {self.current_symbol} | Mode: 🟢 Live Web socket Feed")
        except Exception as e:
            self.status_label.setText(f"Error: {e}")

    def add_category_tab(self):
        name = self.cat_input.text().strip().upper()
        if name:
            lw = QListWidget()
            lw.setStyleSheet("background-color: #1e1e1e; color: #00bcd4; font-weight: bold;")
            lw.itemClicked.connect(self.on_symbol_clicked)
            self.tab_widget.addTab(lw, name)
            self.cat_input.clear()
            self.save_watchlist()

    def open_symbol_picker(self):
        if self.tab_widget.currentIndex() == -1:
            QMessageBox.warning(self, "Warning", "Create or select a tab first!")
            return
        dialog = SymbolSearchDialog(self.master_symbols, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_symbol:
            self.add_to_tab(dialog.selected_symbol)

    def add_to_tab(self, item_text):
        if item_text and self.tab_widget.currentWidget():
            self.tab_widget.currentWidget().addItem(item_text)
            self.save_watchlist()

    def on_symbol_clicked(self, item):
        self.current_symbol = item.text()
        self.header_info_label.setText(f"📈 Active Symbol: {self.current_symbol} | Multi-Candle Order Flow Footprint")

    def save_watchlist(self):
        data = {}
        for i in range(self.tab_widget.count()):
            tab_name = self.tab_widget.tabText(i)
            list_w = self.tab_widget.widget(i)
            symbols = [list_w.item(j).text() for j in range(list_w.count())]
            data[tab_name] = symbols
        with open(self.watchlist_file, 'w') as f:
            json.dump(data, f, indent=4)

    def load_watchlist(self):
        if os.path.exists(self.watchlist_file):
            try:
                with open(self.watchlist_file, 'r') as f:
                    data = json.load(f)
                    for tab_name, symbols in data.items():
                        lw = QListWidget()
                        lw.setStyleSheet("background-color: #1e1e1e; color: #00bcd4; font-weight: bold;")
                        lw.itemClicked.connect(self.on_symbol_clicked)
                        for sym in symbols:
                            lw.addItem(sym)
                        self.tab_widget.addTab(lw, tab_name)
            except Exception:
                pass
        if self.tab_widget.count() == 0:
            lw = QListWidget()
            lw.setStyleSheet("background-color: #1e1e1e; color: #00bcd4; font-weight: bold;")
            lw.itemClicked.connect(self.on_symbol_clicked)
            lw.addItem("NIFTY [NSE]")
            lw.addItem("RELIANCE [NSE]")
            self.tab_widget.addTab(lw, "FAV")


class LoadingWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loading Market Symbols...")
        self.setFixedSize(380, 130)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        
        layout = QVBoxLayout(self)
        self.label = QLabel("⏳ Downloading Live NSE/BSE Symbols...\nPlease Wait...")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-weight: bold; font-size: 13px; color: #00bcd4;")
        layout.addWidget(self.label)
        
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 0)
        layout.addWidget(self.progress)
        self.setStyleSheet("background-color: #222; color: white;")
        
        self.thread = SymbolLoaderThread()
        self.thread.loaded_signal.connect(self.on_loaded)
        self.thread.start()
        
    def on_loaded(self, symbols_list):
        self.symbols_list = symbols_list
        self.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    loader = LoadingWindow()
    if loader.exec_() == QDialog.Accepted:
        win = FootprintApp(loader.symbols_list)
        win.show()
        sys.exit(app.exec_())