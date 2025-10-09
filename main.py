import sys
from PyQt5.QtWidgets import QApplication
from serial_gui import SerialGUI

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SerialGUI()
    window.show()
    sys.exit(app.exec_())