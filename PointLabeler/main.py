import sys
from PyQt5.QtWidgets import QApplication
from ui import MainWindow

def main():
    """Main function to start the application."""
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
