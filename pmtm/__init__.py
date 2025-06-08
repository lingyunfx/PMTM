import sys
from PySide2 import QtWidgets

from pmtm.main_windows import MainWindow


def run():
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
