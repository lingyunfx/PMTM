import os
import sys

from PySide2 import QtWidgets

from pmtm.compat import apply_patches


def get_root_dir():
    """
    资源目录所在的根目录：打包成单文件 exe 后，资源被解压到临时目录，
    取不到解压目录（比如 onedir 打包）时退回 exe 所在目录；未打包时是项目根目录
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
