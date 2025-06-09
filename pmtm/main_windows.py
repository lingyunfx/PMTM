import os
import sys

from PySide2 import QtWidgets, QtCore, QtGui
import dayu_widgets as dy
from dayu_widgets.qt import MIcon

from pmtm.common_widgets import CommonWidget
from pmtm.tool_data import DATA_LIST
from pmtm.settings_dialog import SettingDialog
from pmtm import constant as const
from pmtm.core import user_setting, get_log_file_path



class LeftWidget(CommonWidget):
    """
    左侧功能列表选单
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.list_view = dy.MListView()
        self.switch_theme_bt = dy.MPushButton()
        self.setting_bt = dy.MPushButton()
        self.log_bt = dy.MPushButton()

        self.init_ui()
        self.adjust_ui()
    
    def init_ui(self):
        self.add_widgets_v_line(dy.MLabel('功能列表选单').h4().strong(), self.list_view)
        self.add_widgets_h_line(self.switch_theme_bt, self.setting_bt, self.log_bt, side='right')
        self.setLayout(self.main_layout)
    
    def adjust_ui(self):
        # 设置图标和网格的大小
        self.list_view.setIconSize(QtCore.QSize(35, 35))
        self.list_view.setGridSize(QtCore.QSize(40, 40))
        self.list_view.setAlternatingRowColors(False)

        # 设置按钮的图标和提示
        for bt, icon, tooltip in ((self.setting_bt, r'./resource/setting.png', '设置'),
                                  (self.switch_theme_bt, r'./resource/light.png', '主题'),
                                  (self.log_bt, r'./resource/log.png', '日志')):
            bt.setIcon(MIcon(icon))
            bt.setToolTip(tooltip)
            bt.setMaximumWidth(40)
            bt.setStyleSheet("QPushButton { border: none; }")
        
        # 设置窗口的宽度
        self.setFixedWidth(240)


class MainWindow(CommonWidget):
    """
    主窗口
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.left_widget = LeftWidget(parent=self)
        self.stack = QtWidgets.QStackedWidget(parent=self)

        self.init_ui()
        self.set_data()
        self.adjust_ui()
        self.connect_command()

    def init_ui(self):
        self.add_widgets_h_line(self.left_widget, self.stack)
        self.setLayout(self.main_layout)

    def adjust_ui(self):
        # 设置窗口标题和图标
        self.setWindowTitle(f'{const.WINDOW_TITLE} {const.VERSION}')
        self.setWindowIcon(QtGui.QIcon('./resource/app_icon.png'))

        # 设置主题
        current_user_theme = user_setting.get('theme', 'light')
        theme = dy.MTheme(current_user_theme)
        theme.apply(self)

        # TODO Fix 无法影响的控件处理
        theme.apply(self.stack.widget(3).scan_format_cb)
        theme.apply(self.stack.widget(3).output_format_cb)
        theme.apply(self.stack.widget(3).keyword_type_cb)
        theme.apply(self.stack.widget(3).fps_cb)
        
        # 设置窗口大小
        width = user_setting.get('window_width', 1100)
        height = user_setting.get('window_height', 800)
        self.resize(width, height)
    
    def set_data(self):
        """
        添加功能选单的界面数据
        """
        model = QtGui.QStandardItemModel()
        for item in DATA_LIST:
            if not item.enable:
                continue
            kwargs = {'title': item.name,
                      'description': item.description,
                      'wiki_url': item.wiki_url,
                      'parent': self}
            model.appendRow(QtGui.QStandardItem(QtGui.QIcon(item.icon), item.name))
            self.stack.addWidget(item.widget(**kwargs))
        self.left_widget.list_view.setModel(model)
        self.left_widget.list_view.setCurrentIndex(model.index(0, 0))
        self.left_widget.list_view.setFocusPolicy(QtCore.Qt.NoFocus)

    def connect_command(self):
        self.left_widget.switch_theme_bt.clicked.connect(self.switch_theme_bt_clicked)
        self.left_widget.setting_bt.clicked.connect(self.setting_bt_clicked)
        self.left_widget.log_bt.clicked.connect(self.log_bt_clicked)
        self.left_widget.list_view.clicked.connect(
            lambda index: self.stack.setCurrentIndex(index.row())
        )
    
    def switch_theme_bt_clicked(self):
        # 获取当前主题颜色
        theme_color = user_setting.get('theme', 'light')
        theme_color = 'light' if theme_color == 'dark' else 'dark'
        self.left_widget.switch_theme_bt.setIcon(MIcon(fr'./resource/{theme_color}.png'))

        # 设置主题
        theme = dy.MTheme(theme_color)
        theme.apply(self)
        user_setting.set('theme', theme_color)

        # TODO Fix 无法影响的控件处理
        theme.apply(self.stack.widget(3).scan_format_cb)
        theme.apply(self.stack.widget(3).output_format_cb)
        theme.apply(self.stack.widget(3).keyword_type_cb)
        theme.apply(self.stack.widget(3).fps_cb)
    
    def log_bt_clicked(self):
        # 打开日志文件
        os.startfile(get_log_file_path())

    def setting_bt_clicked(self):
        dialog = SettingDialog(parent=self)
        dialog.ffmpeg = user_setting.get('ffmpeg')
        dialog.ffprobe = user_setting.get('ffprobe')
        dialog.magick = user_setting.get('magick')
        
        if dialog.exec_():
            user_setting.set('ffmpeg', dialog.ffmpeg)
            user_setting.set('ffprobe', dialog.ffprobe)
            user_setting.set('magick', dialog.magick)
    
    def closeEvent(self, event):
        user_setting.set('window_width', self.width())
        user_setting.set('window_height', self.height())
        event.accept()
