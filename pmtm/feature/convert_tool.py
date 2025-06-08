import dayu_widgets as dy
from PySide2 import QtWidgets

from pmtm.common_widgets import CommonToolWidget, DropTabelView
from pmtm.helper import g_pixmap
from pmtm.core import logger, user_setting


HEADER_LIST = [
            {'label': '缩略图', 'key': 'thumbnail', 'icon': g_pixmap},
            {'label': '文件名', 'key': 'shot_name', 'order': 0},
            {'label': '帧数', 'key': 'shot_frame_count', 'align': 'center'},
            {'label': '分辨率', 'key': 'shot_res', 'align': 'center'},
            {'label': '文件路径', 'key': 'source_path'}
        ]

SUPPORT_FRAME_LIST = ['png', 'jpg', 'jpeg', 'tiff', 'exr']
SUPPORT_VIDEO_LIST = ['mov', 'mp4']


class ConvertToolUI(CommonToolWidget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # data
        self.model = dy.MTableModel()

        # widgets
        self.scan_path_line = dy.MLineEdit().folder().small()
        self.scan_bt = dy.MPushButton('扫描').small().primary()
        self.scan_format_cb = QtWidgets.QComboBox()
        self.output_format_cb = QtWidgets.QComboBox()
        self.keyword_line = dy.MLineEdit().small()
        self.keyword_type_cb = QtWidgets.QComboBox()
        self.include_ck = dy.MCheckBox('包括子目录')
        self.method_rb_group = dy.MRadioButtonGroup()
        self.table_view = DropTabelView(show_row_count=True, parent=self)
        self.progress_bar = dy.MProgressBar()
        self.output_path_line = dy.MLineEdit().folder().small()
        self.run_convert_bt = dy.MPushButton('开始转换').small().primary()

        self.setup()
    
    def init_ui(self):
        self.add_widgets_h_line(dy.MLabel('转换方式'), self.method_rb_group, stretch=True)
        self.add_widgets_h_line(dy.MLabel('扫描路径'), self.scan_path_line)
        self.add_widgets_h_line(dy.MLabel('扫描选项'), dy.MLabel('格式'), self.scan_format_cb,
                                dy.MLabel('关键字'), self.keyword_type_cb, self.keyword_line,
                                self.include_ck, self.scan_bt, stretch=True)
        self.add_widgets_v_line(self.table_view)
        self.add_widgets_h_line(dy.MLabel('输出路径'), self.output_path_line, dy.MLabel('输出格式'), self.output_format_cb)
        self.add_widgets_v_line(self.progress_bar, self.run_convert_bt)

    def adjust_ui(self):
        self.progress_bar.setValue(0)
        self.keyword_line.setPlaceholderText('输入关键字过滤')
        self.method_rb_group.set_button_list(['序列帧转视频', '视频转序列帧'])
        self.method_rb_group.set_dayu_checked(0)
        self.keyword_type_cb.addItems(['包含', '不包含'])

        self.scan_format_cb.setFixedWidth(100)
        self.keyword_line.setFixedWidth(130)
        self.output_format_cb.setFixedWidth(100)
        self.keyword_type_cb.setFixedWidth(100)

        self.model.set_header_list(HEADER_LIST)
        self.table_view.setModel(self.model)

        self.method_rb_group_button_changed()
    
    def connect_command(self):
        self.method_rb_group.sig_checked_changed.connect(self.method_rb_group_button_changed)

    def method_rb_group_button_changed(self):
        self.scan_format_cb.clear()
        self.output_format_cb.clear()
        if self.method_rb_group.get_dayu_checked() == 0:
            self.scan_format_cb.addItems(SUPPORT_FRAME_LIST)
            self.output_format_cb.addItems(SUPPORT_VIDEO_LIST)
        else:
            self.scan_format_cb.addItems(SUPPORT_VIDEO_LIST)
            self.output_format_cb.addItems(SUPPORT_FRAME_LIST)
