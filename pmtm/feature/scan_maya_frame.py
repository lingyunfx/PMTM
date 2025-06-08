import re
import csv
import os
import traceback

import dayu_widgets as dy
from PySide2 import QtWidgets, QtGui

from pmtm.common_widgets import CommonToolWidget, PhotoLabel
from pmtm.helper import scan_files
from pmtm.core import logger


HEADER_LIST = [
    {
        'label': '文件名',
        'key': 'file_name'
    },
    {
        'label': '动画开始帧(ast)',
        'key': 'start_frame'
    },
    {
        'label': '动画结束帧(aet)',
        'key': 'end_frame',
        'width': 100,
    },
    {
        'label': '播放起始帧(min)',
        'key': 'min_frame',
        'width': 200,
    },
    {
        'label': '播放结束帧(max)',
        'key': 'max_frame'
    },
    {
        'label': '路径',
        'key': 'file_path'
    }
]


class MayaFrameScanUI(CommonToolWidget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # data
        self.ok_count = 0
        self.error_count = 0
        self.model = dy.MTableModel()

        # widgets
        self.scan_path_line = dy.MLineEdit().folder().small()
        self.scan_bt = dy.MPushButton('扫描').small().primary()
        self.tips_bt = dy.MPushButton('什么是动画开始/结束帧和播放开始/结束帧?').small()
        self.include_ck = dy.MCheckBox('包括子目录')
        self.table_view = dy.MTableView(size=dy.dayu_theme.small, show_row_count=True)
        self.export_bt = dy.MPushButton('导出表格').primary().small()

        self.setup()

    def init_ui(self):
        self.add_widgets_h_line(dy.MLabel('路径'), self.scan_path_line, self.scan_bt, self.include_ck)
        self.add_widgets_v_line(self.tips_bt, self.table_view, self.export_bt)

    def adjust_ui(self):
        self.scan_path_line.setText(r'D:\test\reference_test\2023\scenes')  # for test
        self.tips_bt.setFixedWidth(300)
        self.model.set_header_list(HEADER_LIST)
        self.table_view.setModel(self.model)

    def connect_command(self):
        self.scan_bt.clicked.connect(self.scan_bt_clicked)
        self.export_bt.clicked.connect(self.export_bt_clicked)
        self.tips_bt.clicked.connect(self.tips_bt_clicked)

    def scan_bt_clicked(self):
        # 检查路径
        scan_folder = self.scan_path_line.text()
        if not scan_folder or not os.path.isdir(scan_folder):
            dy.MToast(text='路径不存在!',
                      dayu_type='error',
                      duration=3.0,
                      parent=self).show()
            return

        # 清空数据
        self.model.clear()

        # 扫描文件
        logger.info(f'开始扫描文件, 扫描路径: {scan_folder}')
        files_list = scan_files(scan_folder=scan_folder,
                                is_include=self.include_ck.isChecked(),
                                ext_list=['.ma'])
        logger.info(f'扫描到{len(files_list)}个文件')

        # 获取文件的帧数范围
        for file_path in files_list:
            logger.info(f'扫描文件: {file_path}')
            self.model.append(data_dict=self.scan_file_time_range(file_path=file_path))

        # 自适应表格列宽
        self.table_view.header_view._slot_set_resize_mode(True)

    def export_bt_clicked(self):
        # 获取导出路径
        export_file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Export csv', '', 'CSV Files(*.csv)')
        if not export_file_path:
            return

        # 生成csv数据
        csv_list = [['文件名', '动画开始帧(ast)', '动画结束帧(aet)',
                     '播放起始帧(min)', '播放结束帧(max)', '路径']]
        for data in self.model.get_data_list():
            csv_list.append([data['file_name'], data['start_frame'], data['end_frame'],
                             data['min_frame'], data['max_frame'], data['file_path']])
        
        # 导出csv
        with open(export_file_path, 'w') as f:
            csv_write = csv.writer(f)
            for row in csv_list:
                csv_write.writerow(row)
        logger.info(f'导出完成，文件路径: {export_file_path}')

        # 提示导出完成
        dy.MToast(text='导出完成',
                  dayu_type='success',
                  duration=3.0,
                  parent=self).show()

    def tips_bt_clicked(self):
        tips = PhotoLabel(parent=self)
        tips.exec_()

    def scan_file_time_range(self, file_path):
        """
        通过正则，获取文件的帧数范围，并返回一个字典
        字典格式:
        {
            'file_path': 文件路径,
            'start_frame': 动画开始帧(ast),
            'end_frame': 动画结束帧(aet),
            'min_frame': 播放起始帧(min),
            'max_frame': 播放结束帧(max),
            'file_name': 文件名,
        }
        """

        data_dict = {'file_path': file_path,
                     'start_frame': '',
                     'end_frame': '',
                     'min_frame': '',
                     'max_frame': '',
                     'file_name': os.path.basename(file_path)}
        
        # 尝试不同的编码方式读取文件
        encodings = ['utf-8', 'latin1', 'cp1252']
        content = None

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.readlines()
                break
            except UnicodeDecodeError:
                logger.error(f'文件{file_path}编码错误, {traceback.format_exc()}')
                continue

        if content is None:
            self.error_count += 1
            return data_dict

        # 从文件内容中获取帧数范围
        for line in content:
            if 'playbackOptions' in line:
                pattern = r"-(min|max|ast|aet)\s(\d+)"

                # Find all matches and convert them to a dictionary
                matches = re.findall(pattern, line)
                result_dict = {key: int(value) for key, value in matches}

                data_dict = {'file_path': file_path,
                             'start_frame': result_dict['ast'],
                             'end_frame': result_dict['aet'],
                             'min_frame': result_dict['min'],
                             'max_frame': result_dict['max'],
                             'file_name': os.path.basename(file_path)}
                return data_dict
