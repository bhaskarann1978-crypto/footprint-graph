import os
import sys
import subprocess

# 1. தேவையான கோப்புறைகளின் பட்டியல் (Folder Structure)
FOLDERS = [
    "api",
    "core",
    "ui",
    "plugins",
    "data"
]

# 2. தேவையான பைதான் லைப்ரரிகள் (Dependencies)
REQUIREMENTS = [
    "PyQt5",
    "pyqtgraph",
    "pandas",
    "SmartApi",
    "pyotp",
    "websockets"
]

# 3. மெயின் புரோகிராம் கோடு (Main Application Code)
MAIN_PY_CONTENT = """import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget

class FootprintApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚀 Pro Footprint Terminal (Live & Offline 24/7)")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central Widget & Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.label = QLabel("🟢 System Ready! Modular Architecture Loaded Successfully.")
        self.label.setStyleSheet("font-size: 16px; color: green; font-weight: bold;")
        layout.addWidget(self.label)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = FootprintApp()
    window.show()
    sys.exit(app.exec_())
"""

# 4. பேட்ச்/அப்டேட்டர் கோடு (Auto-Updater Script)
BAT_CONTENT = """@echo off
echo =======================================
echo 🔄 Running System Patch & Updater...
echo =======================================
pip install -r requirements.txt
echo ✅ Update Completed Successfully!
pause
"""

def create_project_structure():
    print("⏳ Creating Project Structure...")
    
    # ஃபோல்டர்களை உருவாக்குதல்
    for folder in FOLDERS:
        os.makedirs(folder, exist_ok=True)
        # ஒவ்வொரு ஃபோல்டரிலும் __init__.py உருவாக்குதல் (மாட்யூலாக மாற்ற)
        with open(os.path.join(folder, "__init__.py"), "w") as f:
            pass
        print(f"  📁 Created Folder: {folder}/")

    # மெயின் ஃபைலை (main.py) உருவாக்குதல்
    with open("main.py", "w", encoding="utf-8") as f:
        f.write(MAIN_PY_CONTENT)
    print("  📄 Created: main.py")

    # update.bat ஃபைலை உருவாக்குதல்
    with open("update.bat", "w", encoding="utf-8") as f:
        f.write(BAT_CONTENT)
    print("  📄 Created: update.bat")

    # requirements.txt உருவாக்குதல்
    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(REQUIREMENTS))
    print("  📄 Created: requirements.txt")

def install_requirements():
    print("\n⏳ Installing Required Python Libraries (PyQt, SmartAPI, etc.)...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Libraries Installed Successfully!")
    except Exception as e:
        print(f"⚠️ Error installing libraries: {e}")
        print("Please run 'pip install -r requirements.txt' manually.")

def launch_app():
    print("\n🚀 Launching Pro Footprint Terminal...")
    subprocess.Popen([sys.executable, "main.py"])

if __name__ == "__main__":
    print("==================================================")
    print(" 🛠️ STARTING MASTER SETUP FOR FOOTPRINT TERMINAL ")
    print("==================================================\n")
    
    create_project_structure()
    install_requirements()
    launch_app()
    
    print("\n🎉 Setup Complete! Your workspace is ready.")