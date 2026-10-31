import os
import sys

from PySide2 import QtWidgets

from pmtm.compat import apply_patches


def get_root_dir():
    """
    资源目录所在的根目录：打包成单文件 exe 后，资源被解压到临时目录，
    Nuitka 通过 __file__ 定位内置资源；源码运行时对应项目根目录。
    同时兼容旧的 PyInstaller 产物。
    """
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run():
    # 代码里的资源路径都写成 './resource/xxx'，先切到根目录，保证在任意位置启动都能找到
    os.chdir(get_root_dir())
    apply_patches()

    from pmtm.main_windows import MainWindow

    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
