import os
import dayu_widgets as dy

from pmtm.core import user_setting
from pmtm.common_widgets import CommonDialog


class SettingDialog(CommonDialog):
    """
    设置面板对话框
    """

    def __init__(self, parent=None):
        super(SettingDialog, self).__init__(parent=parent)

        self.fmg_line = dy.MLineEdit().file(filters=['*.exe']).small()
        self.fpb_line = dy.MLineEdit().file(filters=['*.exe']).small()
        self.mag_line = dy.MLineEdit().file(filters=['*.exe']).small()
        self.save_bt = dy.MPushButton('保存').primary()
        self.cancel_bt = dy.MPushButton('取消')

        self.init_ui()
        self.adjust_ui()
        self.connect_command()

    def init_ui(self):
        self.add_widgets_h_line(dy.MLabel('ffmpeg路径'), self.fmg_line)
        self.add_widgets_h_line(dy.MLabel('ffprobe路径'), self.fpb_line)
        self.add_widgets_h_line(dy.MLabel('magick路径'), self.mag_line)
        self.add_widgets_h_line(self.save_bt, self.cancel_bt)
        self.setLayout(self.main_layout)

    def adjust_ui(self):
        self.setWindowTitle('设置')
        self.resize(400, 150)

    def connect_command(self):
        self.save_bt.clicked.connect(self.accept)
        self.cancel_bt.clicked.connect(self.reject)

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
