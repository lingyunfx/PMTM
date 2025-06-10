import re
import csv
import os
import traceback

import dayu_widgets as dy
from PySide2 import QtWidgets, QtGui, QtCore

from pmtm.common_widgets import CommonToolWidget, PhotoLabel
from pmtm.helper import scan_files, get_resource_file, open_file
from pmtm.core import logger


HEADER_LIST = [
    {'label': '文件名', 'key': 'file_name'},
    {'label': '动画开始帧(ast)', 'key': 'start_frame'},
    {'label': '动画结束帧(aet)', 'key': 'end_frame', 'width': 100},
    {'label': '播放起始帧(min)', 'key': 'min_frame', 'width': 200},
    {'label': '播放结束帧(max)', 'key': 'max_frame'},
    {'label': '路径', 'key': 'file_path', 'width': 1000}
    ]


class MayaFrameScanUI(CommonToolWidget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # data
        self.model = dy.MTableModel()

        # widgets
        self.scan_path_line = dy.MLineEdit().folder().small()
        self.scan_bt = dy.MPushButton('扫描').small().primary()
        self.tips_bt = dy.MPushButton('什么是动画开始/结束帧和播放开始/结束帧?').small()
        self.include_ck = dy.MCheckBox('包括子目录')
        self.table_view = dy.MTableView(size=dy.dayu_theme.small, show_row_count=True)
        self.export_bt = dy.MPushButton('导出表格').primary().small()
        self.after_task_open_ck = dy.MCheckBox('任务完成后打开表格')
        self.total_count_label = dy.MLabel('扫描总数: 0')
        self.error_count_label = dy.MLabel('错误: 0')

        self.setup()

    def init_ui(self):
        self.add_widgets_h_line(dy.MLabel('路径'), self.scan_path_line, self.scan_bt, self.include_ck)
        self.add_widgets_v_line(self.tips_bt, self.table_view)
        self.add_widgets_h_line(self.total_count_label, self.error_count_label, stretch=True)
        self.add_widgets_h_line(self.export_bt, self.after_task_open_ck)

    def adjust_ui(self):
        self.tips_bt.setFixedWidth(300)
        self.model.set_header_list(HEADER_LIST)
        self.table_view.setModel(self.model)
        self.after_task_open_ck.setChecked(True)
        self.after_task_open_ck.setFixedWidth(150)

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
        self.total_count = 0
        self.error_count = 0
        self.model.clear()

        # 开始任务
        self.set_ui_status(freezed=True)
        task = ScanMayaFrameTask(scan_folder=scan_folder,
                                 is_include=self.include_ck.isChecked(),
                                 parent=self)
        task.data_sig.connect(self.add_data_to_table)
        task.finished.connect(self.set_ui_status)
        task.start()
    
    def add_data_to_table(self, data):
        self.total_count += 1

        if data.get('start_frame') == '':
            self.error_count += 1

        self.model.append(data)
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

        # 任务完成后打开表格
        if self.after_task_open_ck.isChecked():
            open_file(export_file_path)

        # 提示导出完成
        dy.MToast(text='导出完成',
                  dayu_type='success',
                  duration=3.0,
                  parent=self).show()

    def tips_bt_clicked(self):
        tips = PhotoLabel(get_resource_file('maya_playback_tips.jpg'), parent=self)
        tips.exec_()
    
    def set_ui_status(self, freezed=False):
        for w in (self.scan_path_line, self.scan_bt, self.include_ck, self.export_bt, self.after_task_open_ck):
            w.setEnabled(not freezed)
        
    @property
    def total_count(self):
        return int(self.total_count_label.text().split(':')[1])

    @total_count.setter
    def total_count(self, value):
        self.total_count_label.setText(f'扫描总数: {value}')

    @property
    def error_count(self):
        return int(self.error_count_label.text().split(':')[1])
    
    @error_count.setter
    def error_count(self, value):
        self.error_count_label.setText(f'错误: {value}')


class ScanMayaFrameTask(QtCore.QThread):

    data_sig = QtCore.Signal(dict)
    
    def __init__(self, scan_folder, is_include, parent=None):
        super().__init__(parent=parent)

        self.scan_folder = scan_folder
        self.is_include = is_include

    def run(self):
        # 扫描ma文件
        logger.info(f'开始扫描文件, 扫描路径: {self.scan_folder}')
        files_list = scan_files(scan_folder=self.scan_folder,
                                is_include=self.is_include,
                                ext_list=('.ma'))

        for file_path in files_list:
            data = self.scan_file_time_range(file_path=file_path)
            self.data_sig.emit(data)
            
    
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
                break
        return data_dict
