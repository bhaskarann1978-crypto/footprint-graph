import sys
import json
import os
import random
import pandas as pd
import requests
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                             QHBoxLayout, QWidget, QPushButton, QMessageBox, 
                             QLineEdit, QFormLayout, QTabWidget, QListWidget, 
                             QDialog, QListWidgetItem, QProgressBar, QTableWidget, 
                             QTableWidgetItem, QHeaderView)
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
                symbols_list = [("RELIANCE", "NSE"), ("TCS", "NSE"), ("BANKBEES", "ETF")]
        except Exception:
            symbols_list = [("RELIANCE", "NSE"), ("TCS", "NSE"), ("BANKBEES", "ETF")]
            
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
        self.search_input.setPlaceholderText("Type to filter (e.g. RELIANCE)...")
        self.search_input.textChanged.connect(self.filter_symbols)
        self.search_input.setStyleSheet("padding: 8px; font-size: 14px;")
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
        self.setWindowTitle("🚀 Pro Visual Footprint & Order Flow Terminal")
        self.setGeometry(100, 100, 1350, 850)
        
        self.watchlist_file = "watchlist.json"
        self.master_symbols = master_symbols
        self.api_manager = None
        self.current_symbol = "RELIANCE [NSE]"
        
        self.init_ui()
        self.load_watchlist()

        # Timer to update live visual footprint matrix simulation
        self.offline_timer = QTimer(self)
        self.offline_timer.timeout.connect(self.simulate_visual_footprint)
        self.offline_timer.start(1000)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left Panel (Credentials, Watchlist, Delete & Bhavcopy)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        title_label = QLabel("🔑 Angel One Credentials")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(title_label)
        
        form_layout = QFormLayout()
        self.api_key_input = QLineEdit()
        self.client_id_input = QLineEdit("CHNA2500")
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.totp_input = QLineEdit()
        self.totp_input.setEchoMode(QLineEdit.Password)
        
        form_layout.addRow("API Key:", self.api_key_input)
        form_layout.addRow("Client ID:", self.client_id_input)
        form_layout.addRow("PIN:", self.pin_input)
        form_layout.addRow("OTP:", self.totp_input)
        left_layout.addLayout(form_layout)
        
        self.login_btn = QPushButton("Login to Live Market")
        self.login_btn.setStyleSheet("background-color: #007ACC; color: white; font-weight: bold; padding: 6px;")
        self.login_btn.clicked.connect(self.execute_login)
        left_layout.addWidget(self.login_btn)
        
        self.status_label = QLabel("🔴 Status: Offline (Visual Footprint Mode)")
        self.status_label.setStyleSheet("font-weight: bold; color: orange;")
        left_layout.addWidget(self.status_label)
        
        watchlist_title = QLabel("📊 Watchlist Tabs")
        watchlist_title.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        left_layout.addWidget(watchlist_title)
        
        cat_layout = QHBoxLayout()
        self.cat_input = QLineEdit()
        self.cat_input.setPlaceholderText("Tab Name...")
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
        
        # Delete Symbol Button
        self.delete_symbol_btn = QPushButton("🗑️ Delete Selected Symbol")
        self.delete_symbol_btn.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 6px;")
        self.delete_symbol_btn.clicked.connect(self.delete_selected_symbol)
        left_layout.addWidget(self.delete_symbol_btn)
        
        # Load Offline Bhavcopy Button
        load_bhav_btn = QPushButton("📂 Load Offline Bhavcopy CSV")
        load_bhav_btn.setStyleSheet("background-color: #6c757d; color: white; font-weight: bold; padding: 6px;")
        load_bhav_btn.clicked.connect(self.load_bhavcopy_offline)
        left_layout.addWidget(load_bhav_btn)
        
        main_layout.addWidget(left_widget, 1)
        
        # Right Panel (Visual Footprint Table Matrix)
        right_panel = QVBoxLayout()
        
        self.header_info_label = QLabel(f"📈 Active Symbol: {self.current_symbol} | Visual Order Flow Footprint")
        self.header_info_label.setStyleSheet("background-color: #111; color: #00bcd4; font-weight: bold; font-size: 14px; padding: 8px;")
        right_panel.addWidget(self.header_info_label)
        
        # Table Grid for Footprint
        self.footprint_table = QTableWidget()
        self.footprint_table.setColumnCount(5)
        self.footprint_table.setHorizontalHeaderLabels(["Price Level", "Bid x Ask (Order Flow)", "Delta (Δ)", "Status / Type", "Total Vol"])
        self.footprint_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.footprint_table.setStyleSheet("""
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
                padding: 4px;
            }
        """)
        right_panel.addWidget(self.footprint_table)
        
        # Status footer bar for Cumulative Delta
        self.footer_status = QLabel("  Cumulative Delta (Cum Δ): +1,450.2K   |   Total Session Volume: 485.6K   |   Market Trend: Bullish 🟢")
        self.footer_status.setStyleSheet("background-color: #1c1c1c; color: #00ffcc; font-weight: bold; font-size: 13px; padding: 8px; border: 1px solid #333;")
        right_panel.addWidget(self.footer_status)
        
        main_layout.addLayout(right_panel, 3)

    def simulate_visual_footprint(self):
        """Populates the footprint table with rich visual colors and values"""
        base_p = random.randint(2450, 2470)
        rows_data = [
            (base_p + 4, "120 x 450", "+330", "Buyers Active", 570, QColor(0, 80, 0)),
            (base_p + 3, "300 x 280", "-20", "Balanced", 580, QColor(40, 40, 40)),
            (base_p + 2, "650 x 150", "-500", "Sellers Active", 800, QColor(80, 0, 0)),
            (base_p + 1, "890 x 920", "+30", "Balanced", 1810, QColor(40, 40, 40)),
            (base_p, "1420 x 2150", "+730", "🔥 POC (Max Vol)", 3570, QColor(0, 100, 100)),
            (base_p - 1, "410 x 190", "-220", "Sellers Active", 600, QColor(40, 40, 40)),
            (base_p - 2, "90 x 540", "+450", "Aggressive Buy", 630, QColor(0, 80, 0)),
            (base_p - 3, "210 x 310", "-100", "Neutral", 520, QColor(40, 40, 40)),
        ]
        
        self.footprint_table.setRowCount(len(rows_data))
        for row_idx, data in enumerate(rows_data):
            price, flow, delta, status, vol, bg_color = data
            
            items = [
                QTableWidgetItem(f"{price}.00"),
                QTableWidgetItem(flow),
                QTableWidgetItem(delta),
                QTableWidgetItem(status),
                QTableWidgetItem(str(vol))
            ]
            
            for col_idx, item in enumerate(items):
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(QBrush(bg_color))
                self.footprint_table.setItem(row_idx, col_idx, item)

    def load_bhavcopy_offline(self):
        """Reads NSE Bhavcopy CSV from data/PR040926 folder automatically"""
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
                    op = row.iloc[0]['OPEN']
                    hi = row.iloc[0]['HIGH']
                    lo = row.iloc[0]['LOW']
                    cl = row.iloc[0]['CLOSE']
                    vol = row.iloc[0].get('TOTTRDQTY', row.iloc[0].get('TTL_TRD_QNT', 0))
                    
                    self.header_info_label.setText(f"📂 Bhavcopy Loaded [{sym_clean}] | O:{op} H:{hi} L:{lo} C:{cl} Vol:{vol}")
                    QMessageBox.information(self, "Success", f"Successfully loaded Bhavcopy data for {sym_clean}!")
                else:
                    QMessageBox.warning(self, "Not Found", f"Symbol '{sym_clean}' not found in this Bhavcopy CSV.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to read CSV: {e}")
        else:
            QMessageBox.warning(self, "Folder Missing", f"No CSV file found inside 'C:\\live FP\\data\\PR040926' folder!")

    def delete_selected_symbol(self):
        """Deletes selected symbol from active watchlist"""
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, QListWidget):
            selected_items = current_tab.selectedItems()
            if selected_items:
                for item in selected_items:
                    current_tab.takeItem(current_tab.row(item))
                self.save_watchlist()
            else:
                QMessageBox.warning(self, "Warning", "Please select a symbol in the watchlist to delete!")
        else:
            QMessageBox.warning(self, "Warning", "No active watchlist tab found!")

    def execute_login(self):
        api_key = self.api_key_input.text().strip()
        client_id = self.client_id_input.text().strip()
        pin = self.pin_input.text().strip()
        totp = self.totp_input.text().strip()
        
        if not all([api_key, client_id, pin, totp]):
            QMessageBox.warning(self, "Warning", "Please fill in all credential fields!")
            return
            
        try:
            self.api_manager = AngelOneManager(api_key, client_id, pin, totp)
            success, msg = self.api_manager.login()
            self.status_label.setText(msg)
            if success:
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                self.header_info_label.setText(f"📈 Active Symbol: {self.current_symbol} | Mode: 🟢 Live WebSocket Feed")
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
        self.header_info_label.setText(f"📈 Active Symbol: {self.current_symbol} | Visual Order Flow Footprint")

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
            lw.addItem("RELIANCE [NSE]")
            lw.addItem("TCS [NSE]")
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