import os
import tempfile
from functools import partial

import openpyxl
from openpyxl.drawing.image import Image
from openpyxl.styles import Font, colors, Alignment
import dayu_widgets as dy
from PySide2 import QtWidgets, QtCore, QtGui

from pmtm.core import logger, user_setting
from pmtm.common_widgets import CommonToolWidget, DropTabelView, message_box
from pmtm.helper import (get_frame_count, extract_thumbnail_from_mov, extract_audio_from_mov,
                         get_image_resolution, get_file_rate, get_file_codex, get_file_resolution,
                         get_file_colorspace, scan_files)


def g_pixmap(name, y):
    """
    用于缩略图显示
    """
    img = y.get('image')
    image_w = 192
    image_h = 108
    result = QtGui.QPixmap(img)
    result = result.scaled(image_w, image_h, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
    return result


# 如果要添加Header，需要在下面的data也添加对应的数据获取方式，定位 if_add_header_list
HEADER_LIST = [
            {'label': '缩略图', 'key': 'thumbnail', 'icon': g_pixmap},
            {'label': '文件名', 'key': 'shot_name', 'order': 0},
            {'label': '帧数', 'key': 'shot_frame_count', 'align': 'center'},
            {'label': '帧数率', 'key': 'shot_fps', 'align': 'center'},
            {'label': '分辨率', 'key': 'shot_res', 'align': 'center'},
            {'label': '编码', 'key': 'shot_codec', 'align': 'center'},
            {'label': '色彩空间', 'key': 'shot_colorspace', 'align': 'center'},
            {'label': '文件路径', 'key': 'source_path'}
        ]


class ScanMovieDataUI(CommonToolWidget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # data
        self.model = dy.MTableModel()

        # widgets
        self.scan_path_line = dy.MLineEdit().folder().small()
        self.scan_bt = dy.MPushButton('扫描').small().primary()
        self.clean_bt = dy.MPushButton('清空').small()
        self.include_ck = dy.MCheckBox('包括子目录')
        self.table_view = DropTabelView(show_row_count=True, parent=self)
        self.export_excel_bt = dy.MPushButton('导出表格').small().primary()
        self.export_audio_bt = dy.MPushButton('导出音频').small().primary()
        self.total_video_label = dy.MLabel('视频总数: 0').strong()
        self.total_frame_label = dy.MLabel('总帧数: 0').strong()

        self.setup()

    def init_ui(self):
        self.add_widgets_h_line(dy.MLabel('路径'), self.scan_path_line, self.scan_bt, self.include_ck)
        self.add_widgets_v_line(self.table_view)
        self.add_widgets_h_line(self.total_video_label, self.total_frame_label, self.clean_bt, stretch=True)
        self.add_widgets_h_line(self.export_excel_bt, self.export_audio_bt)

    def adjust_ui(self):
        self.model.set_header_list(HEADER_LIST)
        self.table_view.setModel(self.model)

    def connect_command(self):
        self.scan_bt.clicked.connect(self.scan_bt_clicked)
        self.export_excel_bt.clicked.connect(self.export_excel_bt_clicked)
        self.export_audio_bt.clicked.connect(self.export_audio_bt_clicked)
        self.clean_bt.clicked.connect(self.clean_bt_clicked)
        self.table_view.fileDropped.connect(partial(self.drop_to_table_function))

    def scan_bt_clicked(self):
        # 清空数据
        self.model.clear()

        #  打印日志
        logger.debug(f'点击扫描按钮, 扫描路径: {self.scan_folder}')

        # 判断文件夹是否存在
        if not self.scan_folder or not os.path.isdir(self.scan_folder):
            dy.MToast(text='路径不存在!',
                      duration=3.0,
                      dayu_type='error',
                      parent=self).show()
            return

        # 获取所有mov路径
        files_list = scan_files(scan_folder=self.scan_folder,
                                is_include=self.include_ck.isChecked(),
                                ext_list=['.mov', '.MOV', '.mp4', '.MP4'])

        if not files_list:
            dy.MToast(text='没有找到文件',
                      duration=3.0,
                      dayu_type='warning',
                      parent=self).show()
            return

        # 将文件列表添加到表格
        self.drop_to_table_function(_list=files_list)

    def export_excel_bt_clicked(self):
        export_file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Export xlsx', '', 'XLSX Files(*.xlsx)')
        if not export_file_path:
            return

        data_list = self.model.get_data_list()

        # 导出表格任务
        task = ExportXLSXTask(data_list=data_list,
                              output_path=export_file_path,
                              parent=self)
        task.finished.connect(partial(message_box, text='导出完成', parent=self))
        task.start()

    def export_audio_bt_clicked(self):
        export_folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Export audio', '')
        if not export_folder_path:
            return

        data_list = self.model.get_data_list()
        # 导出音频对话框
        dialog = ExportAudioDialog(parent=self)

        # 导出音频任务
        task = ExportAudioTask(data_list=data_list,
                               output_folder=export_folder_path,
                               parent=self)
        task.progress_sig.connect(dialog.show_progress)
        task.finished.connect(dialog.show_success)
        task.start()

        # 显示对话框
        dialog.exec_()

    def clean_bt_clicked(self):
        self.model.clear()
        self.total = 0
        self.total_frame = 0

    def scan_before_check(self):
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

    def drop_to_table_function(self, _list):
        # 检查依赖软件
        if not self.scan_before_check():
            return

        # 禁用按钮
        self.disable_all_button()

        # 开始获取视频文件的数据
        task = GetMDataTask(files_list=_list,
                            parent=self)
        task.data_sig.connect(partial(self.add_shot_data))
        task.finished.connect(partial(self.disable_all_button))
        task.start()

    def add_shot_data(self, data):
        logger.debug(f'添加数据: {data}')
        self.model.append(data)

        self.table_view.resizeColumnsToContents()
        self.table_view.resizeRowsToContents()

    def disable_all_button(self):
        for bt in (self.scan_bt, self.export_excel_bt, self.clean_bt):
            bt.setEnabled(not bt.isEnabled())
    
    @property
    def scan_folder(self):
        return self.scan_path_line.text()

    @property
    def total(self):
        text = self.total_video_label.text().split('视频总数: ')[-1]
        return int(text)

    @total.setter
    def total(self, value):
        self.total_video_label.setText(f'视频总数: {value}')

    @property
    def total_frame(self):
        text = self.total_frame_label.text().split('总帧数: ')[-1]
        return int(text)

    @total_frame.setter
    def total_frame(self, value):
        self.total_frame_label.setText(f'总帧数: {value}')


class GetMDataTask(QtCore.QThread):
    """
    获取mov文件数据信息类
    """

    data_sig = QtCore.Signal(dict)

    def __init__(self, files_list, parent=None):
        super(GetMDataTask, self).__init__(parent=parent)
        self.files_list = files_list

    def run(self):
        for source_path in self.files_list:
            self.data_from_file(source_path=source_path)
            self.parent().total += 1

    def data_from_file(self, source_path):
        """
        从文件中获取数据
        """
        file_name = os.path.basename(source_path)
        real_name, ext = os.path.splitext(file_name)

        if ext not in ['.mov', '.MOV', '.mp4', '.MP4']:
            msg = dy.MMessage(text=f'不支持的文件: {source_path}',
                              duration=3.0,
                              dayu_type='warning',
                              parent=self.parent())
            msg.show()
            return

        # 输出一个缩略图
        temp_dir = tempfile.mkdtemp()
        thumbnail_path = os.path.join(temp_dir, 'thumbnail.jpg')
        extract_thumbnail_from_mov(mov_file=source_path,
                                   output_image_file=thumbnail_path)
        image_w, image_h = get_image_resolution(thumbnail_path)

        # if_add_header_list
        data = {'shot_name': real_name,
                'shot_frame_count': get_frame_count(source_path),
                'shot_fps': get_file_rate(source_path),
                'shot_res': get_file_resolution(source_path),
                'shot_codec': get_file_codex(source_path),
                'shot_colorspace': get_file_colorspace(source_path),
                'image': thumbnail_path,
                'image_w': image_w,
                'image_h': image_h,
                'source_path': source_path,
                'thumbnail': ''
                }
        self.parent().total_frame += data.get('shot_frame_count', 0)
        self.data_sig.emit(data)


class ExportAudioDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(ExportAudioDialog, self).__init__(parent=parent)

        # widgets
        self.title = dy.MLabel('导出音频').h2().secondary().strong()
        self.tips_label = dy.MLabel('')
        self.progress = dy.MProgressBar()
        self.close_bt = dy.MPushButton('程序正在运行').small()

        # init ui
        self.layout = QtWidgets.QVBoxLayout()
        for widget in (self.title, self.tips_label, self.progress, self.close_bt):
            self.layout.addWidget(widget)
        self.setLayout(self.layout)
        self.setFixedWidth(300)
        self.setWindowTitle('进度显示')

    def show_progress(self, progress_data_list):
        shot_name, current, total = progress_data_list
        self.tips_label.setText(f'正在导出: {current}/{total} {shot_name}')
        self.progress.setValue(int(current / total * 100))

    def show_success(self):
        self.close_bt.setText('任务完成，关闭')
        self.close_bt.clicked.connect(self.close)
        self.tips_label.setText('导出完成!')


class ExportAudioTask(QtCore.QThread):
    """
    导出音频任务
    """

    progress_sig = QtCore.Signal(list)

    def __init__(self, data_list, output_folder, parent=None):
        super(ExportAudioTask, self).__init__(parent=parent)
        self.data_list = data_list
        self.output_folder = output_folder

    def run(self):
        current = 1
        total = len(self.data_list)

        for data in self.data_list:
            self.progress_sig.emit([data['shot_name'], current, total])
            wav_path = os.path.join(self.output_folder, f'{data["shot_name"]}.wav')
            extract_audio_from_mov(mov_file=data['source_path'], output_audio_file=wav_path)
            current += 1


class ExportXLSXTask(QtCore.QThread):

    def __init__(self, data_list, output_path, parent=None):
        super(ExportXLSXTask, self).__init__(parent=parent)

        self.data_list = data_list
        self.output_path = output_path

        title = [header['label'] for header in HEADER_LIST]
        self.xls_data = [title]

    def run(self):
        for data in self.data_list:
            # 缩略图的key实际为image，这里列表排除它，之后添加
            item_list = [str(data[header['key']]) for header in HEADER_LIST if header['key'] != 'thumbnail']
            item_list.insert(0, data['image'])
            self.xls_data.append(item_list)

        self.make_xsl()

    def make_xsl(self):
        if not self.xls_data:
            return

        wb = openpyxl.Workbook()
        sheet = wb.active
        columns = self.generate_alphabet_list(len(self.xls_data[0]))

        for data in self.xls_data:
            # row 为行数
            row = self.xls_data.index(data) + 1
            if row != 1:
                sheet.row_dimensions[row].height = 108 / 1.333333
            for column in columns:
                sheet.column_dimensions[column].width = 190.0 / 8.2121 + 0.63
                position = '{0}{1}'.format(column, row)
                _index = columns.index(column)
                if row != 1 and _index == 0:
                    # 如果不是第一行标题，且是第一列，则设置图片大小
                    img = Image(data[_index])
                    img.width, img.height = (192, 108)
                    sheet.add_image(img, position)
                else:
                    # 其它均为字符
                    sheet[position].value = data[_index]
                    sheet[position].alignment = Alignment(horizontal='center', vertical='center')
                    t_font = Font(name='Heiti SC Light', size=12)
                    sheet[position].font = t_font

        wb.save(self.output_path)

    @staticmethod
    def generate_alphabet_list(length):
        return [chr(i) for i in range(ord('A'), ord('A') + length)]
