import os
import tempfile
from functools import partial

import dayu_widgets as dy
from PySide2 import QtWidgets, QtCore, QtGui

from pmtm.helper import g_pixmap, check_depend_tool_exist, open_file
from pmtm.core import logger
from pmtm.common_widgets import CommonToolWidget, DropTabelView
from pmtm.media_utils import extract_thumbnail_from_image, run_collage_images


SUPPORTED_EXT = ['.png', '.jpg', '.jpeg', '.tiff', '.exr', '.JPG', '.JPEG', '.TIFF', '.EXR', '.PNG']
HEADER_LIST = [
            {'label': '缩略图', 'key': 'thumbnail', 'icon': g_pixmap},
            {'label': '文件名', 'key': 'file_name', 'order': 0},
            {'label': '文件路径', 'key': 'file_path'}
        ]


class ImageCollageUI(CommonToolWidget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # data
        self.model = dy.MTableModel()

        # widgets
        self.clean_bt = dy.MPushButton('清空所有').small()
        self.table_view = DropTabelView(show_row_count=True, parent=self)
        self.horizontal_count_box = dy.MSpinBox().small()
        self.vertical_count_box = dy.MSpinBox().small()
        self.output_bt = dy.MPushButton('输出').small().primary()
        self.auto_set_bt = dy.MCheckBox('自动设置横纵向个数（默认正方形）')
        self.open_file_ck = dy.MCheckBox('导出后打开文件')

        self.setup()

    def init_ui(self):
        self.add_widgets_h_line(self.clean_bt, dy.MLabel('提示: 鼠标右键可单独删除选择的条目').secondary())
        self.add_widgets_v_line(self.table_view)
        self.add_widgets_h_line(dy.MLabel('输出选项'), dy.MLabel('水平数量'), self.horizontal_count_box,
                                dy.MLabel('垂直数量'), self.vertical_count_box, self.auto_set_bt, self.open_file_ck,
                                stretch=True)
        self.add_widgets_h_line(self.output_bt)
    
    def adjust_ui(self):
        self.clean_bt.setFixedWidth(130)
        self.horizontal_count_box.setFixedWidth(100)
        self.vertical_count_box.setFixedWidth(100)
        self.horizontal_count_box.setRange(1, 100)
        self.vertical_count_box.setRange(1, 100)
        self.horizontal_count_box.setEnabled(False)
        self.vertical_count_box.setEnabled(False)
        self.auto_set_bt.setChecked(True)
        self.open_file_ck.setChecked(True)

        self.model.set_header_list(HEADER_LIST)
        self.table_view.setModel(self.model)
        self.table_view.enable_context_menu(enable=True)

    def connect_command(self):
        self.table_view.fileDropped.connect(partial(self.drop_to_table_function))
        self.output_bt.clicked.connect(self.output_bt_clicked)
        self.auto_set_bt.stateChanged.connect(self.auto_set_bt_clicked)
        self.clean_bt.clicked.connect(self.clean_bt_clicked)
        self.table_view.sig_context_menu.connect(self.slot_context_menu)

    def drop_to_table_function(self, _list):
        if not check_depend_tool_exist():
            dy.MToast(text='请设置依赖软件路径',
                      duration=3.0,
                      dayu_type='error',
                      parent=self).show()
            return
        
        self.set_ui_status(freezed=True)
        task = DropImageTask(files_list=_list, parent=self)
        task.data_sig.connect(self.add_data_to_table)
        task.finished.connect(self.set_ui_status)
        task.start()

    def add_data_to_table(self, data):
        self.model.append(data)
        self.table_view.resizeColumnsToContents()
        self.table_view.resizeRowsToContents()
        self.auto_calc_v_h_count()
    
    def slot_context_menu(self, data):
        if not data.selection:
            return
        selections = data.selection
        if selections:
            self.create_context_menu(selections=selections)
    
    def create_context_menu(self, selections):
        menu = dy.MMenu(parent=self.table_view)
        menu.addAction('从表格中删除', partial(self.remove_item, selections))
        menu.exec_(QtGui.QCursor.pos())
    
    def remove_item(self, selections):
        for sel in selections:
            self.model.remove(sel)

        self.table_view.resizeColumnsToContents()
        self.table_view.resizeRowsToContents()

    def output_bt_clicked(self):
        # 获取保存路径
        export_file_path, _ = QtWidgets.QFileDialog.getSaveFileName(parent=self,
                                                                    caption='导出图片',
                                                                    filter=f'图片 (*{" *".join(SUPPORTED_EXT[:4])})')
        if not export_file_path:
            return
        
        image_files = [data['file_path'] for data in self.model.get_data_list()]
        run_collage_images(image_files=image_files,
                           output_image_file=export_file_path,
                           horizontal_count=self.horizontal_count_box.value(),
                           vertical_count=self.vertical_count_box.value())
        dy.MToast(text='导出成功',
                  duration=3.0,
                  dayu_type='success',
                  parent=self).show()

        if self.open_file_ck.isChecked():
            open_file(export_file_path)
    
    def set_ui_status(self, freezed=False):
        for w in (self.horizontal_count_box, self.vertical_count_box, self.output_bt):
            w.setEnabled(not freezed)

    def auto_set_bt_clicked(self, state):
        if state == QtCore.Qt.Checked:
            self.auto_calc_v_h_count()
            self.horizontal_count_box.setEnabled(False)
            self.vertical_count_box.setEnabled(False)
        else:
            self.horizontal_count_box.setEnabled(True)
            self.vertical_count_box.setEnabled(True)
    
    def auto_calc_v_h_count(self):
        total_count = self.model.rowCount()
        if total_count == 0:
            return
        
        # 计算横纵向个数
        # 计算最接近正方形的横纵向个数
        horizontal_count = int(total_count ** 0.5)
        if horizontal_count * horizontal_count < total_count:
            horizontal_count += 1
        vertical_count = horizontal_count
        
        self.horizontal_count_box.setValue(horizontal_count)
        self.vertical_count_box.setValue(vertical_count)

    def clean_bt_clicked(self):
        self.model.clear()
        self.auto_calc_v_h_count()


class DropImageTask(QtCore.QThread):

    data_sig = QtCore.Signal(dict)

    def __init__(self, files_list, parent=None):
        super().__init__(parent=parent)

        self.files_list = files_list
    
    def run(self):
        for file_path in self.files_list:
            ext = os.path.splitext(file_path)[1]
            if ext not in SUPPORTED_EXT:
                logger.error(f'不支持的文件类型: {file_path}')
                continue

            tmp_dir = tempfile.mkdtemp()
            thumb_path = os.path.join(tmp_dir, 'thumbnail.jpg')
            extract_thumbnail_from_image(image_file=file_path,
                                         output_image_file=thumb_path)
            
            data = {
                'thumbnail': '',
                'file_name': os.path.basename(file_path),
                'file_path': file_path,
                'image': thumb_path
            }
            self.data_sig.emit(data)
