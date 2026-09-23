import sys

from PySide6.QtWidgets import QApplication
from src.interface.mainWindow import Window

def main():
    app = QApplication(sys.argv)

    window = Window()
    window.show()
    sys.exit(app.exec())
    

if __name__ == "__main__":
    main()