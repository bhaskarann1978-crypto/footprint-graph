import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                             QHBoxLayout, QWidget, QPushButton, QMessageBox, 
                             QLineEdit, QFormLayout, QTreeWidget, QTreeWidgetItem,
                             QInputDialog)
from api.angel_login import AngelOneManager

class FootprintApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚀 Pro Footprint Terminal (Categories & Symbols Manager)")
        self.setGeometry(100, 100, 1200, 800)
        
        # Undo & Redo History Stacks
        self.undo_stack = []
        self.redo_stack = []
        
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # --- LEFT PANEL (Credentials & Categorized Watchlist) ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        title_label = QLabel("🔑 Angel One Credentials")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        left_layout.addWidget(title_label)
        
        # Form Input Fields for Login
        form_layout = QFormLayout()
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter API Key")
        
        self.client_id_input = QLineEdit()
        self.client_id_input.setPlaceholderText("Enter Client ID")
        self.client_id_input.setText("CHNA2500") # Default Client ID
        
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
        self.login_btn.setMinimumHeight(35)
        self.login_btn.setStyleSheet("background-color: #007ACC; color: white; font-weight: bold;")
        self.login_btn.clicked.connect(self.execute_login)
        left_layout.addWidget(self.login_btn)
        
        self.status_label = QLabel("🔴 Status: Offline")
        self.status_label.setStyleSheet("font-weight: bold; padding: 5px; color: red;")
        left_layout.addWidget(self.status_label)
        
        # --- WATCHLIST MANAGEMENT SECTION ---
        watchlist_title = QLabel("📊 Watchlist Management")
        watchlist_title.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        left_layout.addWidget(watchlist_title)
        
        # 1. Category Actions Layout (Add & Rename)
        cat_layout = QHBoxLayout()
        self.cat_input = QLineEdit()
        self.cat_input.setPlaceholderText("Category Name (e.g. ETFs)")
        
        self.add_cat_btn = QPushButton("+ Cat")
        self.add_cat_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        self.add_cat_btn.clicked.connect(self.add_category)
        
        self.rename_cat_btn = QPushButton("✏️ Rename")
        self.rename_cat_btn.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold;")
        self.rename_cat_btn.clicked.connect(self.rename_category)
        
        cat_layout.addWidget(self.cat_input)
        cat_layout.addWidget(self.add_cat_btn)
        cat_layout.addWidget(self.rename_cat_btn)
        left_layout.addLayout(cat_layout)
        
        # 2. Symbol Actions Layout (Add Symbol)
        sym_layout = QHBoxLayout()
        self.sym_input = QLineEdit()
        self.sym_input.setPlaceholderText("Symbol (e.g. RELIANCE)")
        
        self.add_sym_btn = QPushButton("+ Symbol")
        self.add_sym_btn.setStyleSheet("background-color: #17a2b8; color: white; font-weight: bold;")
        self.add_sym_btn.clicked.connect(self.add_symbol)
        
        sym_layout.addWidget(self.sym_input)
        sym_layout.addWidget(self.add_sym_btn)
        left_layout.addLayout(sym_layout)
        
        # 3. Tree Widget for Categories & Symbols
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("My Watchlist Tree")
        left_layout.addWidget(self.tree_widget)
        
        # 4. Undo, Delete, Redo Buttons Layout
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
        
        # 5. Instruction Text with Medium Font Size
        self.note_label = QLabel("⚠️ Note: Please select an item before clicking Delete")
        self.note_label.setStyleSheet("color: #444; font-size: 15px; font-style: italic; font-weight: bold;")
        left_layout.addWidget(self.note_label)
        
        # --- RIGHT PANEL (Chart Area Placeholder) ---
        right_panel = QVBoxLayout()
        chart_placeholder = QLabel("📈 Footprint Chart Rendering Area (Live Tick Stream Ready)")
        chart_placeholder.setStyleSheet("background-color: #2b2b2b; color: #ffffff; font-size: 15px; qproperty-alignment: AlignCenter;")
        right_panel.addWidget(chart_placeholder)
        
        # Add panels to main layout
        main_layout.addWidget(left_widget, 1)
        main_layout.addLayout(right_panel, 3)

    def execute_login(self):
        api_key = self.api_key_input.text().strip()
        client_id = self.client_id_input.text().strip()
        pin = self.pin_input.text().strip()
        totp_code = self.totp_input.text().strip()
        
        if not all([api_key, client_id, pin, totp_code]):
            QMessageBox.warning(self, "Warning", "Please fill in all the credential fields!")
            return
            
        self.status_label.setText("⏳ Authenticating...")
        self.status_label.setStyleSheet("color: orange; font-weight: bold; padding: 5px;")
        
        try:
            self.api_manager = AngelOneManager(api_key, client_id, pin, totp_code)
            success, message = self.api_manager.login()
            
            self.status_label.setText(message)
            if success:
                self.status_label.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
                self.login_btn.setEnabled(False)
                self.login_btn.setText("✅ Logged In Successfully")
                self.api_key_input.setReadOnly(True)
                self.client_id_input.setReadOnly(True)
                self.pin_input.setReadOnly(True)
                self.totp_input.setReadOnly(True)
            else:
                self.status_label.setStyleSheet("color: red; font-weight: bold; padding: 5px;")
        except Exception as e:
            self.status_label.setText(f"🔴 Error: {str(e)}")
            self.status_label.setStyleSheet("color: red; font-weight: bold; padding: 5px;")

    def add_category(self):
        cat_name = self.cat_input.text().strip().upper()
        if cat_name:
            item = QTreeWidgetItem(self.tree_widget)
            item.setText(0, f"📁 {cat_name}")
            
            # Log for Undo/Redo
            self.undo_stack.append(('add_cat', cat_name))
            self.redo_stack.clear()
            self.cat_input.clear()
        else:
            QMessageBox.warning(self, "Warning", "Please enter a valid Category name!")

    def rename_category(self):
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select a Category from the list to rename!")
            return
            
        target_item = selected_items[0]
        if target_item.parent() is not None:
            QMessageBox.warning(self, "Warning", "Please select a main Category, not a symbol, to rename!")
            return
            
        current_name = target_item.text(0).replace("📁 ", "")
        new_name, ok = QInputDialog.getText(self, "Rename Category", "Enter new category name:", QLineEdit.Normal, current_name)
        
        if ok and new_name.strip():
            new_cleaned = new_name.strip().upper()
            target_item.setText(0, f"📁 {new_cleaned}")

    def add_symbol(self):
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select a Category first from the list where you want to add the symbol!")
            return
            
        target_item = selected_items[0]
        if target_item.parent() is not None:
            target_item = target_item.parent()
            
        cat_name = target_item.text(0).replace("📁 ", "")
        symbol = self.sym_input.text().strip().upper()
        if symbol:
            child_item = QTreeWidgetItem(target_item)
            child_item.setText(0, f"📌 {symbol} (Live)")
            target_item.setExpanded(True)
            
            # Log for Undo/Redo
            self.undo_stack.append(('add_sym', cat_name, symbol))
            self.redo_stack.clear()
            self.sym_input.clear()
        else:
            QMessageBox.warning(self, "Warning", "Please enter a valid Stock or ETF symbol!")

    def delete_item(self):
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select an item before clicking Delete!")
            return
            
        for item in selected_items:
            parent = item.parent()
            if parent is None:
                # Root Category deletion
                cat_name = item.text(0).replace("📁 ", "")
                symbols = [item.child(i).text(0).replace("📌 ", "").replace(" (Live)", "") for i in range(item.childCount())]
                root_index = self.tree_widget.indexOfTopLevelItem(item)
                self.tree_widget.takeTopLevelItem(root_index)
                
                # Log for Undo/Redo
                self.undo_stack.append(('del_cat', cat_name, symbols))
                self.redo_stack.clear()
            else:
                # Symbol deletion
                parent_cat = parent.text(0).replace("📁 ", "")
                symbol_text = item.text(0).replace("📌 ", "").replace(" (Live)", "")
                parent.removeChild(item)
                
                # Log for Undo/Redo
                self.undo_stack.append(('del_sym', parent_cat, symbol_text))
                self.redo_stack.clear()

    def undo_action(self):
        if not self.undo_stack:
            QMessageBox.information(self, "Info", "Nothing to undo!")
            return
            
        action = self.undo_stack.pop()
        self.redo_stack.append(action)
        action_type = action[0]
        
        if action_type == 'add_cat':
            cat_name = action[1]
            for i in range(self.tree_widget.topLevelItemCount()):
                item = self.tree_widget.topLevelItem(i)
                if item.text(0).replace("📁 ", "") == cat_name:
                    self.tree_widget.takeTopLevelItem(i)
                    break
        elif action_type == 'add_sym':
            cat_name, sym_name = action[1], action[2]
            for i in range(self.tree_widget.topLevelItemCount()):
                cat_item = self.tree_widget.topLevelItem(i)
                if cat_item.text(0).replace("📁 ", "") == cat_name:
                    for j in range(cat_item.childCount()):
                        child = cat_item.child(j)
                        if sym_name in child.text(0):
                            cat_item.removeChild(child)
                            break
                    break
        elif action_type == 'del_cat':
            cat_name, symbols = action[1], action[2]
            item = QTreeWidgetItem(self.tree_widget)
            item.setText(0, f"📁 {cat_name}")
            for sym in symbols:
                child = QTreeWidgetItem(item)
                child.setText(0, f"📌 {sym} (Live)")
            item.setExpanded(True)
        elif action_type == 'del_sym':
            cat_name, sym_name = action[1], action[2]
            for i in range(self.tree_widget.topLevelItemCount()):
                cat_item = self.tree_widget.topLevelItem(i)
                if cat_item.text(0).replace("📁 ", "") == cat_name:
                    child = QTreeWidgetItem(cat_item)
                    child.setText(0, f"📌 {sym_name} (Live)")
                    cat_item.setExpanded(True)
                    break

    def redo_action(self):
        if not self.redo_stack:
            QMessageBox.information(self, "Info", "Nothing to redo!")
            return
            
        action = self.redo_stack.pop()
        self.undo_stack.append(action)
        action_type = action[0]
        
        if action_type == 'add_cat':
            cat_name = action[1]
            item = QTreeWidgetItem(self.tree_widget)
            item.setText(0, f"📁 {cat_name}")
        elif action_type == 'add_sym':
            cat_name, sym_name = action[1], action[2]
            for i in range(self.tree_widget.topLevelItemCount()):
                cat_item = self.tree_widget.topLevelItem(i)
                if cat_item.text(0).replace("📁 ", "") == cat_name:
                    child = QTreeWidgetItem(cat_item)
                    child.setText(0, f"📌 {sym_name} (Live)")
                    cat_item.setExpanded(True)
                    break
        elif action_type == 'del_cat':
            cat_name = action[1]
            for i in range(self.tree_widget.topLevelItemCount()):
                item = self.tree_widget.topLevelItem(i)
                if item.text(0).replace("📁 ", "") == cat_name:
                    self.tree_widget.takeTopLevelItem(i)
                    break
        elif action_type == 'del_sym':
            cat_name, sym_name = action[1], action[2]
            for i in range(self.tree_widget.topLevelItemCount()):
                cat_item = self.tree_widget.topLevelItem(i)
                if cat_item.text(0).replace("📁 ", "") == cat_name:
                    for j in range(cat_item.childCount()):
                        child = cat_item.child(j)
                        if sym_name in child.text(0):
                            cat_item.removeChild(child)
                            break
                    break

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = FootprintApp()
    window.show()
    sys.exit(app.exec_())