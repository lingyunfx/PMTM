import os
import traceback
import tempfile
from functools import partial

import dayu_widgets as dy
from dayu_path import DayuPath
from PySide2 import QtWidgets, QtCore, QtGui

from pmtm.helper import g_pixmap
from pmtm.core import logger, user_setting
from pmtm.common_widgets import CommonToolWidget, DropTabelView, question_box, message_box
from pmtm.media_utils import (get_image_resolution, get_video_resolution, get_video_frame_count,
                              extract_thumbnail_from_image, extract_thumbnail_from_mov,
                              convert_seq_to_video, convert_video_to_seq, convert_seq_to_seq,
                              convert_video_to_video)


HEADER_LIST = [
            {'label': '缩略图', 'key': 'thumbnail', 'icon': g_pixmap},
            {'label': '文件名', 'key': 'file_name', 'order': 0},
            {'label': '起始帧', 'key': 'start_frame', 'align': 'center'},
            {'label': '结束帧', 'key': 'end_frame', 'align': 'center'},
            {'label': '帧数', 'key': 'frame_count', 'align': 'center'},
            {'label': '分辨率', 'key': 'resolution', 'align': 'center'},
            {'label': '文件路径', 'key': 'file_path'}
        ]

SUPPORT_FRAME_LIST = ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.exr', '.dpx', '.tga']
SUPPORT_VIDEO_LIST = ['.mov', '.mp4']


class ConvertToolUI(CommonToolWidget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # data
        self.model = dy.MTableModel()

        # widgets
        self.scan_path_line = dy.MLineEdit().folder().small()
        self.scan_bt = dy.MPushButton('扫描').small().primary()
        self.scan_format_cb = dy.MComboBox().small()
        self.output_format_cb = dy.MComboBox().small()
        self.keyword_line = dy.MLineEdit().small()
        self.keyword_type_cb = dy.MComboBox().small()
        self.include_ck = dy.MCheckBox('包括子目录')
        self.table_view = DropTabelView(show_row_count=True, parent=self)
        self.progress_bar = dy.MProgressBar()
        self.output_path_line = dy.MLineEdit().folder().small()
        self.run_convert_bt = dy.MPushButton('开始转换').small().primary()
        self.start_frame_box = dy.MSpinBox().small()
        self.fps_box = dy.MComboBox().small()

        self.setup()
    
    def init_ui(self):
        self.add_widgets_h_line(dy.MLabel('扫描选项'), dy.MLabel('格式'), self.scan_format_cb,
                                dy.MLabel('关键字'), self.keyword_type_cb, self.keyword_line,
                                self.include_ck, stretch=True)
        self.add_widgets_h_line(dy.MLabel('扫描路径'), self.scan_path_line, self.scan_bt)
        self.add_widgets_v_line(self.table_view)
        self.add_widgets_h_line(dy.MLabel('输出选项'), dy.MLabel('帧率'), self.fps_box,
                                dy.MLabel('图片序列起始帧'), self.start_frame_box,
                                dy.MLabel('输出格式'), self.output_format_cb, stretch=True)
        self.add_widgets_h_line(dy.MLabel('输出路径'), self.output_path_line)
        self.add_widgets_v_line(self.progress_bar, self.run_convert_bt)

    def adjust_ui(self):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.keyword_line.setPlaceholderText('输入关键字过滤')
        self.keyword_type_cb.addItems(['包含', '不包含'])
        self.include_ck.setChecked(True)
        self.scan_format_cb.addItems(SUPPORT_FRAME_LIST + SUPPORT_VIDEO_LIST)
        self.output_format_cb.addItems(SUPPORT_FRAME_LIST + SUPPORT_VIDEO_LIST)

        self.fps_box.addItems(['23.976', '24', '25', '29.97', '30'])
        self.fps_box.setCurrentText('25')
        self.fps_box.setFixedWidth(70)
        self.start_frame_box.setSuffix('帧')
        self.start_frame_box.setRange(1, 1000000000)
        self.start_frame_box.setValue(1001)

        self.scan_format_cb.setFixedWidth(100)
        self.keyword_line.setFixedWidth(130)
        self.output_format_cb.setFixedWidth(100)
        self.keyword_type_cb.setFixedWidth(100)

        self.model.set_header_list(HEADER_LIST)
        self.table_view.setModel(self.model)
        self.table_view.enable_context_menu(enable=True)

    def connect_command(self):
        self.scan_bt.clicked.connect(self.scan_bt_clicked)
        self.run_convert_bt.clicked.connect(self.run_convert_bt_clicked)
        self.table_view.sig_context_menu.connect(self.slot_context_menu)
    
    def scan_bt_clicked(self):
        logger.debug(f'扫描按钮点击')

        # 检查依赖软件
        if not self.task_before_check():
            return

        # 清空数据
        self.model.clear()
        self.progress_bar.setValue(0)

        # 收集扫描参数
        scan_folder = self.scan_path_line.text()
        is_include = self.include_ck.isChecked()
        ext_tuple = (self.input_ext, self.input_ext.upper())
        keyword = self.keyword_line.text()
        keyword_type = self.keyword_type_cb.currentText()

        if not keyword:
            function_filter = None
        elif keyword_type == '包含':
            function_filter = lambda x: keyword in x
        else:
            function_filter = lambda x: keyword not in x

        # 检查扫描路径
        if not scan_folder or not os.path.isdir(scan_folder):
            dy.MToast(text='路径不存在!',
                      duration=3.0,
                      dayu_type='error',
                      parent=self).show()
            return

        # 开始扫描
        self.set_ui_status(freezed=True)
        self.scan_task = ScanTask(scan_folder=scan_folder,
                                  is_include=is_include,
                                  ext_tuple=ext_tuple,
                                  function_filter=function_filter,
                                  parent=self)
        self.scan_task.data_sig.connect(self.add_data_to_table)
        self.scan_task.is_success_sig.connect(self.task_finished)
        self.scan_task.finished.connect(self.set_ui_status)
        self.scan_task.start()

    def run_convert_bt_clicked(self):
        # 检查依赖软件
        if not self.task_before_check():
            return

        # 询问用户确认转换，避免重复误点
        if not question_box(text='是否开始格式转换？',
                            parent=self):
            return

        # 收集转换参数
        if self.input_ext in SUPPORT_FRAME_LIST and self.output_ext in SUPPORT_VIDEO_LIST:
            convert_method = 'img_to_video'
        elif self.input_ext in SUPPORT_VIDEO_LIST and self.output_ext in SUPPORT_FRAME_LIST:
            convert_method = 'video_to_img'
        elif self.input_ext in SUPPORT_FRAME_LIST and self.output_ext in SUPPORT_FRAME_LIST:
            convert_method = 'img_to_img'
        elif self.input_ext in SUPPORT_VIDEO_LIST and self.output_ext in SUPPORT_VIDEO_LIST:
            convert_method = 'video_to_video'
        else:
            return
        
        output_settings = {
            'convert_method': convert_method,
            'output_ext': self.output_ext,
            'fps': self.fps_box.currentText(),
            'start_frame': self.start_frame_box.value()
        }

        # 检查输出路径
        output_folder = self.output_path_line.text()
        if not output_folder or not os.path.isdir(output_folder):
            dy.MToast(text='路径不存在!',
                      duration=3.0,
                      dayu_type='error',
                      parent=self).show()
            return
        
        # 开始任务
        self.set_ui_status(freezed=True)
        task = ConvertTask(data_list=self.model.get_data_list(),
                           output_settings=output_settings,
                           output_folder=output_folder,
                           parent=self)
        task.progress_sig.connect(self.progress_bar.setValue)
        task.is_success_sig.connect(self.task_finished)
        task.finished.connect(self.set_ui_status)
        task.start()

    def add_data_to_table(self, data):
        logger.debug(f'添加数据: {data}')
        self.model.append(data)

        self.table_view.resizeColumnsToContents()
        self.table_view.resizeRowsToContents()
    
    def slot_context_menu(self, data):
        if not data.selection:
            return
        selections = data.selection
        if selections:
            self.create_context_menu(selections=selections)
    
    def create_context_menu(self, selections):
        menu = dy.MMenu(parent=self.table_view)
        menu.addAction('从列表删除', partial(self.remove_item, selections))
        menu.exec_(QtGui.QCursor.pos())
    
    def remove_item(self, selections):
        for sel in selections:
            self.model.remove(sel)

        self.table_view.resizeColumnsToContents()
        self.table_view.resizeRowsToContents()
    
    def task_finished(self, is_success):
        text = '任务完成' if is_success else '任务失败，请检查日志！'
        progress_bar_status = dy.MProgressBar.NormalStatus if is_success else dy.MProgressBar.ErrorStatus
        self.progress_bar.set_dayu_status(progress_bar_status)
        message_box(text=text,
                    success=is_success,
                    parent=self)
    
    def set_ui_status(self, freezed=False):
        for w in (self.scan_path_line, self.scan_bt, self.scan_format_cb, self.output_format_cb, self.keyword_line,
                  self.keyword_type_cb, self.include_ck, self.output_path_line, self.fps_box, self.start_frame_box,
                  self.output_format_cb, self.run_convert_bt
                  ):
            w.setEnabled(not freezed)
    
    def task_before_check(self):
        """
        检查依赖软件
        """
        ffmpeg = user_setting.get('ffmpeg')
        ffprobe = user_setting.get('ffprobe')
        magick = user_setting.get('magick')

        if not all([ffmpeg, ffprobe, magick]):
            dy.MToast(text='请先设置依赖软件路径',
                      duration=3.0,
                      dayu_type='error',
                      parent=self).show()
            return False
        return True
    
    @property
    def input_ext(self):
        return self.scan_format_cb.currentText()

    @property
    def output_ext(self):
        return self.output_format_cb.currentText()
    

class ScanTask(QtCore.QThread):
    """
    扫描任务类
    """

    data_sig = QtCore.Signal(dict)
    is_success_sig = QtCore.Signal(bool)

    def __init__(self, scan_folder, is_include, ext_tuple, function_filter, parent=None):
        super().__init__(parent=parent)

        self.scan_folder = DayuPath(scan_folder)
        self.is_include = is_include
        self.ext_tuple = ext_tuple
        self.function_filter = function_filter

    def run(self):
        try:
            logger.debug(f'开始扫描任务')
            
            for seq_file in self.scan_folder.scan(recursive=self.is_include,
                                                  ext_filters=self.ext_tuple,
                                                  function_filter=self.function_filter):
                
                logger.debug(f'扫描到文件: {seq_file}')
                ext = seq_file.ext
                temp_dir = tempfile.mkdtemp()
                thumbnail_path = os.path.join(temp_dir, 'thumbnail.jpg')
                file_name = seq_file.stem.stem

                if ext in SUPPORT_FRAME_LIST:
                    first_file = seq_file.restore_pattern(seq_file.frames[0])
                    extract_thumbnail_from_image(first_file, thumbnail_path)
                    image_w, image_h = get_image_resolution(first_file)
                    shot_res = f'{image_w}x{image_h}'
                    start_frame = seq_file.frames[0]
                    end_frame = seq_file.frames[-1]
                    frame_count = len(seq_file.frames)
                elif ext in SUPPORT_VIDEO_LIST:
                    extract_thumbnail_from_mov(seq_file, thumbnail_path)
                    shot_res = get_video_resolution(seq_file)
                    start_frame = 1
                    end_frame = get_video_frame_count(seq_file)
                    frame_count = end_frame
                else:
                    continue

                data = {'thumbnail': '',
                        'file_name': file_name,
                        'start_frame': start_frame,
                        'end_frame': end_frame,
                        'frame_count': frame_count,
                        'resolution': shot_res,
                        'file_path': seq_file,
                        'image': thumbnail_path,
                        'dayu_path': seq_file}
                self.data_sig.emit(data)
                logger.debug(f'添加数据: {data}')

            self.is_success_sig.emit(True)

        except Exception as e:
            logger.error(f'扫描失败: {e}')
            logger.error(f'{traceback.format_exc()}')
            self.is_success_sig.emit(False)
            return


class ConvertTask(QtCore.QThread):
    """
    转换任务类
    """

    progress_sig = QtCore.Signal(int)
    is_success_sig = QtCore.Signal(bool)

    def __init__(self, data_list, output_settings, output_folder, parent=None):
        super().__init__(parent=parent)

        self.data_list = data_list
        self.output_settings = output_settings
        self.output_folder = output_folder

    def run(self):
        try:
            # 获取进度条步长
            current_progress = 0
            each_progress = 100 / len(self.data_list)

            # 获取转换方法和输出格式
            convert_method = self.output_settings['convert_method']
            output_ext = self.output_settings['output_ext']

            # 开始转换
            for data in self.data_list:
                # 更新进度条
                current_progress += each_progress
                self.progress_sig.emit(current_progress)

                # 获取输出文件路径
                output_file = os.path.join(self.output_folder, data['file_name'] + output_ext)

                # 根据不同的转换方法，执行不同的函数
                if convert_method == 'img_to_video':
                    convert_seq_to_video(seq_file=data['dayu_path'],
                                        output_video_file=output_file,
                                        start_frame=data['dayu_path'].frames[0],
                                        fps=self.output_settings.get('fps', 25)
                                        )
                elif convert_method == 'video_to_img':
                    seq_output_path = self.get_seq_output_path(data=data)                
                    convert_video_to_seq(video_file=data['dayu_path'],
                                        output_seq_file=seq_output_path,
                                        start_frame=self.output_settings.get('start_frame', 1)
                                        )
                elif convert_method == 'img_to_img':
                    seq_output_path = self.get_seq_output_path(data=data)
                    convert_seq_to_seq(source_seq_file=data['dayu_path'],
                                       output_seq_file=seq_output_path,
                                       source_start_frame=data['dayu_path'].frames[0],
                                       output_start_frame=self.output_settings.get('start_frame', 1)
                                       )
                elif convert_method == 'video_to_video':
                    convert_video_to_video(source_video_file=data['dayu_path'],
                                           output_video_file=output_file)
                else:
                    continue
            
            self.is_success_sig.emit(True)

        except Exception as e:
            logger.error(f'转换失败: {e}')
            logger.error(f'{traceback.format_exc()}')
            self.is_success_sig.emit(False)
            return

    def get_seq_output_path(self, data):
        """
        获取序列帧的输出路径格式
        """
        start_frame = self.output_settings.get('start_frame', 1)
        output_ext = self.output_settings.get('output_ext', '.mov')
        frame_count = data['frame_count']
        num_len = len(str(start_frame+frame_count))
        if num_len <= 4:
            output_path = os.path.join(self.output_folder, data['file_name'], f'{data["file_name"]}.%04d{output_ext}')
        else:
            num_len = str(num_len).zfill(2)
            output_path = os.path.join(self.output_folder, data['file_name'], f'{data["file_name"]}.%{num_len}d{output_ext}')
        
        dir_path = os.path.dirname(output_path)
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)
            logger.debug(f'创建序列输出路径: {dir_path}')

        return output_path
