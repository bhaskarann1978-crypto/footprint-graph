import sys
import json
import os
import requests
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                             QHBoxLayout, QWidget, QPushButton, QMessageBox, 
                             QLineEdit, QFormLayout, QTabWidget, QListWidget, 
                             QInputDialog, QDialog, QListWidgetItem)
from PyQt5.QtCore import Qt
from api.angel_login import AngelOneManager

class SymbolSearchDialog(QDialog):
    def __init__(self, symbols_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Search & Select Market Symbols (NSE/BSE/ETFs)")
        self.setGeometry(200, 200, 450, 550)
        self.selected_symbol = None
        self.symbols_list = symbols_list  # List of (symbol, segment) tuples
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Search Box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to filter (e.g. JUBLINGREA, REL)...")
        self.search_input.textChanged.connect(self.filter_symbols)
        self.search_input.setStyleSheet("padding: 8px; font-size: 14px;")
        layout.addWidget(self.search_input)
        
        # List Widget
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("background-color: #1e1e1e; color: #00bcd4; font-weight: bold; font-size: 14px;")
        self.list_widget.itemDoubleClicked.connect(self.accept_symbol)
        layout.addWidget(self.list_widget)
        
        self.populate_list(self.symbols_list)
        
        # Action Buttons Layout
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
            QMessageBox.warning(self, "Warning", "Please select a symbol from the list first!")


class FootprintApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚀 Pro Footprint Terminal (Live API Symbol Finder)")
        self.setGeometry(100, 100, 1200, 800)
        
        self.undo_stack = []
        self.redo_stack = []
        self.watchlist_file = "watchlist.json"
        
        # Fetching Live Symbols as List from Angel One Scrip Master API
        self.master_symbols = self.fetch_live_market_symbols()
        
        self.init_ui()
        self.load_watchlist()

    def fetch_live_market_symbols(self):
        """Fetch live NSE and BSE symbols as a list to support both exchanges separately"""
        symbols_list = []
        seen = set()
        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        try:
            response = requests.get(url, timeout=10)
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
                                
                print(f"Successfully loaded {len(symbols_list)} live symbols from Angel One API!")
            else:
                symbols_list = [("RELIANCE", "NSE"), ("TCS", "NSE"), ("JUBLINGREA", "NSE"), ("JUBLINGREA", "BSE"), ("BANKBEES", "ETF")]
        except Exception as e:
            print(f"Error fetching live market symbols: {e}")
            symbols_list = [("RELIANCE", "NSE"), ("TCS", "NSE"), ("JUBLINGREA", "NSE"), ("JUBLINGREA", "BSE"), ("BANKBEES", "ETF")]
            
        return symbols_list

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # --- SEPARATE EXPAND BUTTON ---
        self.expand_btn = QPushButton(">>")
        self.expand_btn.setFixedWidth(35)
        self.expand_btn.setFixedHeight(50)
        self.expand_btn.setStyleSheet("font-weight: bold; background-color: #333; color: #00bcd4; font-size: 16px; border-radius: 4px;")
        self.expand_btn.clicked.connect(self.toggle_left_panel)
        self.expand_btn.hide()
        main_layout.addWidget(self.expand_btn)
        
        # --- LEFT PANEL ---
        self.left_widget = QWidget()
        left_layout = QVBoxLayout(self.left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Collapse Toggle Header
        toggle_layout = QHBoxLayout()
        title_label = QLabel("🔑 Angel One Credentials")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.collapse_btn = QPushButton("<<")
        self.collapse_btn.setFixedWidth(40)
        self.collapse_btn.setStyleSheet("font-weight: bold; background-color: #444; color: white;")
        self.collapse_btn.clicked.connect(self.toggle_left_panel)
        
        toggle_layout.addWidget(title_label)
        toggle_layout.addStretch()
        toggle_layout.addWidget(self.collapse_btn)
        left_layout.addLayout(toggle_layout)
        
        # Credentials Form
        form_layout = QFormLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter API Key")
        self.client_id_input = QLineEdit()
        self.client_id_input.setText("CHNA2500")
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setPlaceholderText("Enter 4-digit PIN")
        self.totp_input = QLineEdit()
        self.totp_input.setEchoMode(QLineEdit.Password)
        self.totp_input.setPlaceholderText("Enter 6-digit OTP")
        
        form_layout.addRow("API Key:", self.api_key_input)
        form_layout.addRow("Client ID:", self.client_id_input)
        form_layout.addRow("PIN:", self.pin_input)
        form_layout.addRow("OTP:", self.totp_input)
        left_layout.addLayout(form_layout)
        
        self.login_btn = QPushButton("Login to Angel One")
        self.login_btn.setMinimumHeight(33)
        self.login_btn.setStyleSheet("background-color: #007ACC; color: white; font-weight: bold;")
        self.login_btn.clicked.connect(self.execute_login)
        left_layout.addWidget(self.login_btn)
        
        self.status_label = QLabel("🔴 Status: Offline")
        self.status_label.setStyleSheet("font-weight: bold; padding: 3px; color: red;")
        left_layout.addWidget(self.status_label)
        
        # Watchlist Tabs Management
        watchlist_title = QLabel("📊 Watchlist Tabs & Symbols")
        watchlist_title.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 5px;")
        left_layout.addWidget(watchlist_title)
        
        # Category Tab Layout
        cat_layout = QHBoxLayout()
        self.cat_input = QLineEdit()
        self.cat_input.setPlaceholderText("Tab Name (e.g. 1, Weekly)")
        
        self.add_cat_btn = QPushButton("+ Tab")
        self.add_cat_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        self.add_cat_btn.clicked.connect(self.add_category_tab)
        
        self.rename_cat_btn = QPushButton("✏️ Rename")
        self.rename_cat_btn.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold;")
        self.rename_cat_btn.clicked.connect(self.rename_category_tab)
        
        cat_layout.addWidget(self.cat_input)
        cat_layout.addWidget(self.add_cat_btn)
        cat_layout.addWidget(self.rename_cat_btn)
        left_layout.addLayout(cat_layout)
        
        # Symbol Picker Button
        self.open_picker_btn = QPushButton("🔍 Open Market Symbol Finder (+ Symbol)")
        self.open_picker_btn.setMinimumHeight(35)
        self.open_picker_btn.setStyleSheet("background-color: #17a2b8; color: white; font-weight: bold; font-size: 13px;")
        self.open_picker_btn.clicked.connect(self.open_symbol_picker)
        left_layout.addWidget(self.open_picker_btn)
        
        # Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab_handler)
        left_layout.addWidget(self.tab_widget)
        
        # Action Buttons
        action_layout = QHBoxLayout()
        self.undo_btn = QPushButton("↩️ Undo")
        self.delete_btn = QPushButton("🗑️ Delete")
        self.redo_btn = QPushButton("🔁 Redo")
        
        self.undo_btn.setStyleSheet("font-weight: bold;")
        self.delete_btn.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")
        self.redo_btn.setStyleSheet("font-weight: bold;")
        
        self.undo_btn.clicked.connect(self.undo_action)
        self.delete_btn.clicked.connect(self.delete_item)
        self.redo_btn.clicked.connect(self.redo_action)
        
        action_layout.addWidget(self.undo_btn)
        action_layout.addWidget(self.delete_btn)
        action_layout.addWidget(self.redo_btn)
        left_layout.addLayout(action_layout)
        
        # Note Statement
        self.note_label = QLabel("⚠️ Note: Please select an item before clicking Delete")
        self.note_label.setStyleSheet("color: #444; font-size: 13px; font-style: italic; font-weight: bold;")
        left_layout.addWidget(self.note_label)
        
        main_layout.addWidget(self.left_widget, 1)
        
        # --- RIGHT PANEL ---
        right_panel = QVBoxLayout()
        chart_placeholder = QLabel("📈 Footprint Chart Rendering Area (Live Tick Stream Ready)")
        chart_placeholder.setStyleSheet("background-color: #2b2b2b; color: #ffffff; font-size: 15px; qproperty-alignment: AlignCenter;")
        right_panel.addWidget(chart_placeholder)
        
        main_layout.addLayout(right_panel, 3)

    def toggle_left_panel(self):
        if self.left_widget.isVisible():
            self.left_widget.hide()
            self.expand_btn.show()
        else:
            self.left_widget.show()
            self.expand_btn.hide()

    def add_tab_with_name(self, name):
        list_widget = QListWidget()
        list_widget.setStyleSheet("background-color: #1e1e1e; color: #00bcd4; font-weight: bold; font-size: 13px;")
        self.tab_widget.addTab(list_widget, name)
        self.save_watchlist()

    def execute_login(self):
        api_key = self.api_key_input.text().strip()
        client_id = self.client_id_input.text().strip()
        pin = self.pin_input.text().strip()
        totp_code = self.totp_input.text().strip()
        
        if not all([api_key, client_id, pin, totp_code]):
            QMessageBox.warning(self, "Warning", "Please fill in all the credential fields!")
            return
            
        self.status_label.setText("⏳ Authenticating...")
        self.status_label.setStyleSheet("color: orange; font-weight: bold; padding: 3px;")
        
        try:
            self.api_manager = AngelOneManager(api_key, client_id, pin, totp_code)
            success, message = self.api_manager.login()
            
            self.status_label.setText(message)
            if success:
                self.status_label.setStyleSheet("color: green; font-weight: bold; padding: 3px;")
                self.login_btn.setEnabled(False)
                self.login_btn.setText("✅ Logged In Successfully")
                self.api_key_input.setReadOnly(True)
                self.client_id_input.setReadOnly(True)
                self.pin_input.setReadOnly(True)
                self.totp_input.setReadOnly(True)
            else:
                self.status_label.setStyleSheet("color: red; font-weight: bold; padding: 3px;")
        except Exception as e:
            self.status_label.setText(f"🔴 Error: {str(e)}")
            self.status_label.setStyleSheet("color: red; font-weight: bold; padding: 3px;")

    def add_category_tab(self):
        tab_name = self.cat_input.text().strip().upper()
        if tab_name:
            self.add_tab_with_name(tab_name)
            self.undo_stack.append(('add_tab', tab_name))
            self.redo_stack.clear()
            self.cat_input.clear()
        else:
            QMessageBox.warning(self, "Warning", "Please enter a valid Tab Name!")

    def rename_category_tab(self):
        current_index = self.tab_widget.currentIndex()
        if current_index == -1:
            QMessageBox.warning(self, "Warning", "No active tab selected to rename!")
            return
            
        current_name = self.tab_widget.tabText(current_index)
        new_name, ok = QInputDialog.getText(self, "Rename Tab", "Enter new tab name:", QLineEdit.Normal, current_name)
        
        if ok and new_name.strip():
            cleaned_name = new_name.strip().upper()
            self.tab_widget.setTabText(current_index, cleaned_name)
            self.save_watchlist()

    def open_symbol_picker(self):
        current_index = self.tab_widget.currentIndex()
        if current_index == -1:
            QMessageBox.warning(self, "Warning", "Please select a Tab first where you want to add symbols!")
            return
            
        dialog = SymbolSearchDialog(self.master_symbols, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_symbol:
            symbol = dialog.selected_symbol
            current_tab_name = self.tab_widget.tabText(current_index)
            current_list = self.tab_widget.currentWidget()
            
            existing_items = [current_list.item(i).text() for i in range(current_list.count())]
            if symbol in existing_items:
                QMessageBox.information(self, "Info", f"Symbol '{symbol}' already exists in this tab!")
                return
                
            current_list.addItem(symbol)
            self.undo_stack.append(('add_sym', current_tab_name, symbol))
            self.redo_stack.clear()
            self.save_watchlist()

    def delete_item(self):
        current_index = self.tab_widget.currentIndex()
        if current_index == -1:
            QMessageBox.warning(self, "Warning", "Please select an item before clicking Delete!")
            return
            
        current_list = self.tab_widget.currentWidget()
        selected_items = current_list.selectedItems()
        
        if selected_items:
            for item in selected_items:
                sym_text = item.text()
                row = current_list.row(item)
                current_list.takeItem(row)
                tab_name = self.tab_widget.tabText(current_index)
                self.undo_stack.append(('del_sym', tab_name, sym_text))
                self.redo_stack.clear()
            self.save_watchlist()
        else:
            tab_name = self.tab_widget.tabText(current_index)
            reply = QMessageBox.question(self, "Delete Tab", f"No symbol selected. Do you want to delete tab '{tab_name}'?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                symbols = [current_list.item(i).text() for i in range(current_list.count())]
                self.tab_widget.removeTab(current_index)
                self.undo_stack.append(('del_tab', tab_name, symbols, current_index))
                self.redo_stack.clear()
                self.save_watchlist()

    def close_tab_handler(self, index):
        tab_name = self.tab_widget.tabText(index)
        current_list = self.tab_widget.widget(index)
        symbols = [current_list.item(i).text() for i in range(current_list.count())]
        self.tab_widget.removeTab(index)
        self.undo_stack.append(('del_tab', tab_name, symbols, index))
        self.redo_stack.clear()
        self.save_watchlist()

    def save_watchlist(self):
        data = {}
        for i in range(self.tab_widget.count()):
            tab_name = self.tab_widget.tabText(i)
            list_w = self.tab_widget.widget(i)
            symbols = [list_w.item(j).text() for j in range(list_w.count())]
            data[tab_name] = symbols
        try:
            with open(self.watchlist_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving watchlist: {e}")

    def load_watchlist(self):
        if os.path.exists(self.watchlist_file):
            try:
                with open(self.watchlist_file, 'r') as f:
                    data = json.load(f)
                    for tab_name, symbols in data.items():
                        list_widget = QListWidget()
                        list_widget.setStyleSheet("background-color: #1e1e1e; color: #00bcd4; font-weight: bold; font-size: 13px;")
                        for sym in symbols:
                            list_widget.addItem(sym)
                        self.tab_widget.addTab(list_widget, tab_name)
            except Exception as e:
                print(f"Error loading watchlist: {e}")
        else:
            for name in ["1", "2", "3"]:
                self.add_tab_with_name(name)

    def undo_action(self):
        if not self.undo_stack:
            QMessageBox.information(self, "Info", "Nothing to undo!")
            return
            
        action = self.undo_stack.pop()
        self.redo_stack.append(action)
        action_type = action[0]
        
        if action_type == 'add_tab':
            tab_name = action[1]
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == tab_name:
                    self.tab_widget.removeTab(i)
                    break
        elif action_type == 'add_sym':
            tab_name, sym_name = action[1], action[2]
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == tab_name:
                    list_w = self.tab_widget.widget(i)
                    for j in range(list_w.count()):
                        if list_w.item(j).text() == sym_name:
                            list_w.takeItem(j)
                            break
                    break
        elif action_type == 'del_sym':
            tab_name, sym_name = action[1], action[2]
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == tab_name:
                    list_w = self.tab_widget.widget(i)
                    list_w.addItem(sym_name)
                    break
        elif action_type == 'del_tab':
            tab_name, symbols, index = action[1], action[2], action[3]
            list_w = QListWidget()
            list_w.setStyleSheet("background-color: #1e1e1e; color: #00bcd4; font-weight: bold; font-size: 13px;")
            for sym in symbols:
                list_w.addItem(sym)
            self.tab_widget.insertTab(index, list_w, tab_name)
        self.save_watchlist()

    def redo_action(self, event=None):
        if not self.redo_stack:
            QMessageBox.information(self, "Info", "Nothing to redo!")
            return
            
        action = self.redo_stack.pop()
        self.undo_stack.append(action)
        action_type = action[0]
        
        if action_type == 'add_tab':
            tab_name = action[1]
            self.add_tab_with_name(tab_name)
        elif action_type == 'add_sym':
            tab_name, sym_name = action[1], action[2]
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == tab_name:
                    list_w = self.tab_widget.widget(i)
                    list_w.addItem(sym_name)
                    break
        elif action_type == 'del_sym':
            tab_name, sym_name = action[1], action[2]
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == tab_name:
                    list_w = self.tab_widget.widget(i)
                    for j in range(list_w.count()):
                        if list_w.item(j).text() == sym_name:
                            list_w.takeItem(j)
                            break
                    break
        elif action_type == 'del_tab':
            tab_name, symbols, index = action[1], action[2], action[3]
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == tab_name:
                    self.tab_widget.removeTab(i)
                    break
        self.save_watchlist()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = FootprintApp()
    window.show()
    sys.exit(app.exec_())