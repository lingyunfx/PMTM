import webbrowser
from functools import partial
from abc import ABCMeta, abstractmethod

import dayu_widgets as dy
from PySide2 import QtWidgets, QtCore, QtGui
from dayu_widgets.qt import MIcon

from pmtm.core import logger
from pmtm.helper import get_image_path


class WidgetMixin(object):


    def __init__(self):
        self.main_layout = QtWidgets.QVBoxLayout()

    def add_widgets_v_line(self, *args, side=None, stretch=False):
        return self.__add_widgets(*args, side=side, stretch=stretch, layout_type=QtWidgets.QVBoxLayout)

    def add_widgets_h_line(self, *args, side=None, stretch=False):
        return self.__add_widgets(*args, side=side, stretch=stretch, layout_type=QtWidgets.QHBoxLayout)

    def __add_widgets(self, *args, side=None, stretch=False, layout_type=None):
        layout = layout_type()

        side_dict = {'right': QtCore.Qt.AlignRight,
                     'left': QtCore.Qt.AlignLeft,
                     'top': QtCore.Qt.AlignTop,
                     'center': QtCore.Qt.AlignCenter
                     }
        if side:
            layout.setAlignment(side_dict.get(side, QtCore.Qt.AlignTop))

        for item in args:
            if isinstance(item, QtWidgets.QLayout):
                layout.addLayout(item)
            elif isinstance(item, QtWidgets.QWidget):
                layout.addWidget(item)

        if stretch:
            layout.addStretch(stretch)

        self.main_layout.addLayout(layout)

        return layout


class CommonDialog(QtWidgets.QDialog, WidgetMixin):

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        WidgetMixin.__init__(self)


class CommonWidget(QtWidgets.QWidget, WidgetMixin):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        WidgetMixin.__init__(self)


QtMeta = type(QtWidgets.QDialog)


class CommonToolWidgetMeta(ABCMeta, QtMeta):
    pass


class CommonToolWidget(CommonWidget):
    """
    工具主界面基类
    """

    __metaclass__ = CommonToolWidgetMeta

    def __init__(self, title, description, wiki_url, parent=None):
        super().__init__(parent=parent)

        # widgets
        label = dy.MLabel(title).h3().strong().secondary()
        desc = dy.MLabel(description).code().strong()
        self.help_bt = dy.MPushButton('').small()

        # layout
        self.add_widgets_h_line(label, self.help_bt)
        self.add_widgets_h_line(desc)
        self.setLayout(self.main_layout)

        # adjust widgets
        self.help_bt.setIcon(MIcon(r'./resource/help.png'))
        self.help_bt.setMaximumWidth(30)
        self.help_bt.setToolTip('Open wiki page')

        # connect_command
        self.help_bt.clicked.connect(partial(self.open_wiki_url, wiki_url))

    def setup(self):
        self.init_ui()
        self.adjust_ui()
        self.connect_command()

    @abstractmethod
    def init_ui(self):
        """
        Layout for widgets
        """
        pass

    @abstractmethod
    def adjust_ui(self):
        """
        Adjusting widgets size attributes, etc
        """
        pass

    @abstractmethod
    def connect_command(self):
        """
        Connecting signals and slots
        """
        pass

    def open_wiki_url(self, url):
        """
        Open the help documentation page
        """
        if not url:
            dy.MMessage(text='暂时没有文档!', duration=3.0, parent=self)
            return
        webbrowser.open(url)


class InfoBoard(QtWidgets.QTextBrowser):
    """
    信息显示组件
    """

    def __init__(self, parent=None):
        super(InfoBoard, self).__init__(parent=parent)
        self.setStyleSheet('border: 1px solid rgba(0, 0, 0, 0.1)')
        self.setPlaceholderText('这里会显示一些日志信息..')

    def add_line(self, text):
        logger.info(text)
        if text.startswith('[error]'):
            typ = 'error'
            text = text.replace('[error]', '')
        elif text.startswith('[warning]'):
            typ = 'warning'
            text = text.replace('[warning]', '')
        elif text.startswith('[pass]'):
            typ = 'pass'
            text = text.replace('[pass]', '')
        else:
            typ = None

        color = {'error': 'red',
                 'warning': 'yellow',
                 'pass': 'green'}.get(typ)

        if color:
            text = '<font color="{0}" <{0}>{1}</font>'.format(color, text)

        self.append(text)
        QtWidgets.QApplication.processEvents()


class DropTabelView(dy.MTableView):
    """
    支持拖拽功能的表格组件
    """

    fileDropped = QtCore.Signal(list)  # 文件拖拽完成信号

    def __init__(self, size=None, show_row_count=False, parent=None):
        super().__init__(size=size, show_row_count=show_row_count, parent=parent)
        self.setAcceptDrops(True)  # 启用拖拽功能

    def _handle_url_mime_data(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            return True
        event.ignore()
        return False

    def dragEnterEvent(self, event):
        self._handle_url_mime_data(event)

    def dragMoveEvent(self, event):
        self._handle_url_mime_data(event)

    def dropEvent(self, event):
        if self._handle_url_mime_data(event):
            links = [str(url.toLocalFile()) for url in event.mimeData().urls()]
            self.fileDropped.emit(links)


class ListWidgetWithLabel(CommonWidget):
    """
    带标签的列表组件
    """

    def __init__(self, label, parent=None):
        super(ListWidgetWithLabel, self).__init__(parent=parent)
        self.label = dy.MLabel(label).h4().secondary().strong()
        self.widget = QtWidgets.QListWidget(parent=self)
        self.init_ui()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

    def init_ui(self):
        lay = self.add_widgets_v_line(self.label, self.widget)
        lay.setSpacing(0)
        self.setLayout(self.main_layout)


def message_box(text, success=True, parent=None):
    """
    消息框组件
    """
    pix = QtGui.QPixmap('resource/success.png') if success else QtGui.QPixmap('resource/error.png')
    message = QtWidgets.QMessageBox(parent)
    message.setWindowTitle('提示')
    message.setText(text)
    message.setIconPixmap(pix)
    message.addButton('OK', QtWidgets.QMessageBox.YesRole)
    message.exec_()


def question_box(text, parent=None):
    """
    一个询问对话框，选择是或者否，对应返回True或False
    """
    answer = QtWidgets.QMessageBox.question(parent,
                                            '提示',
                                            text,
                                            QtWidgets.QMessageBox.Yes |
                                            QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No,
                                            )
    if answer != QtWidgets.QMessageBox.Yes:
        return
    return True


class PhotoLabel(QtWidgets.QDialog):
    """
    显示一张图片的label
    """

    def __init__(self, parent=None):
        super(PhotoLabel, self).__init__(parent=parent)
        main_layout = QtWidgets.QHBoxLayout()
        image_path = get_image_path('maya_playback_tips.jpg')
        label = QtWidgets.QLabel()
        label.setPixmap(QtGui.QPixmap(image_path))
        main_layout.addWidget(label)
        self.setLayout(main_layout)