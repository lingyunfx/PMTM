import os
import webbrowser
import dayu_widgets as dy


from pmtm.constant import HELP_URL, DOWNLOAD_URL, FOLLOW_PIC, GIT_URL
from pmtm.common_widgets import CommonDialog, PhotoLabel


class SettingDialog(CommonDialog):
    """
    设置面板对话框
    """

    def __init__(self, parent=None):
        super(SettingDialog, self).__init__(parent=parent)

        self.fmg_line = dy.MLineEdit().file(filters=['*.exe']).small()
        self.fpb_line = dy.MLineEdit().file(filters=['*.exe']).small()
        self.mag_line = dy.MLineEdit().file(filters=['*.exe']).small()
        self.help_bt = dy.MPushButton('帮助文档').small()
        self.download_bt = dy.MPushButton('下载页面 (工具更新发布地址)').small()
        self.follow_bt = dy.MPushButton('关注公众号').small()
        self.git_bt = dy.MPushButton('Github项目地址').small()

        self.init_ui()
        self.adjust_ui()
        self.connect_command()

    def init_ui(self):
        self.add_widgets_v_line(dy.MLabel('依赖路径设置').h4().secondary(), dy.MDivider())
        self.add_widgets_h_line(dy.MLabel('ffmpeg路径'), self.fmg_line)
        self.add_widgets_h_line(dy.MLabel('ffprobe路径'), self.fpb_line)
        self.add_widgets_h_line(dy.MLabel('magick路径'), self.mag_line)
        self.add_widgets_v_line(dy.MLabel('关于').h4().secondary(), dy.MDivider())
        self.add_widgets_v_line(self.help_bt, self.download_bt, self.git_bt, self.follow_bt)
        self.setLayout(self.main_layout)

    def adjust_ui(self):
        self.setWindowTitle('设置')
        self.resize(400, 150)

    def connect_command(self):
        self.follow_bt.clicked.connect(self.follow_bt_clicked)
        self.help_bt.clicked.connect(self.help_bt_clicked)
        self.download_bt.clicked.connect(self.download_bt_clicked)
        self.git_bt.clicked.connect(self.git_bt_clicked)

    def follow_bt_clicked(self):
        PhotoLabel(FOLLOW_PIC, parent=self).exec_()
    
    def help_bt_clicked(self):
        webbrowser.open(HELP_URL)
    
    def download_bt_clicked(self):
        webbrowser.open(DOWNLOAD_URL)
    
    def git_bt_clicked(self):
        webbrowser.open(GIT_URL)

    def closeEvent(self, event):
        self.accept()

    @property
    def ffmpeg(self):
        return self.fmg_line.text()

    @property
    def magick(self):
        return self.mag_line.text()

    @property
    def ffprobe(self):
        return self.fpb_line.text()
    
    @ffmpeg.setter
    def ffmpeg(self, value):
        self.fmg_line.setText(value)
    
    @magick.setter
    def magick(self, value):
        self.mag_line.setText(value)
    
    @ffprobe.setter
    def ffprobe(self, value):
        self.fpb_line.setText(value)
