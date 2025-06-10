import os
import tempfile
import shutil
from functools import partial

import dayu_widgets as dy
from PySide2 import QtWidgets, QtCore, QtGui

from pmtm.helper import g_pixmap, check_depend_tool_exist
from pmtm.core import logger
from pmtm.common_widgets import CommonToolWidget, DropTabelView, MenuPushButton, CommonDialog
from pmtm.media_utils import extract_thumbnail_from_image, run_add_text_to_image, run_collage_images


def _color(x, y):
    return QtGui.QColor(y.get('color'))


SUPPORTED_EXT = ['.png', '.jpg', '.jpeg', '.tiff', '.exr', '.JPG', '.JPEG', '.TIFF', '.EXR', '.PNG']
HEADER_LIST = [
            {'label': '缩略图', 'key': 'thumbnail', 'icon': g_pixmap},
            {'label': '文件名', 'key': 'file_name', 'order': 0, 'align': 'center'},
            {'label': '文字', 'key': 'text', 'color': _color, 'align': 'center'},
            {'label': '文字大小', 'key': 'size', 'align': 'center'},
            {'label': '文件路径', 'key': 'file_path'}
        ]


class AddTextToImageUI(CommonToolWidget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # data
        self.model = dy.MTableModel()

        # widgets
        self.table_view = DropTabelView(show_row_count=True, parent=self)
        self.clear_bt = dy.MPushButton('清空所有').small()
        self.save_ext_cb = MenuPushButton().small()
        self.run_bt = dy.MPushButton('开始任务').small().primary()
        self.export_type_rb = dy.MRadioButtonGroup()
        self.tips_label = dy.MLabel('')

        self.setup()

    def init_ui(self):
        self.add_widgets_h_line(self.clear_bt, dy.MLabel('提示: 在表格中，选中条目后右键菜单，可以添加文字，修改颜色').strong())
        self.add_widgets_v_line(self.table_view)
        self.add_widgets_h_line(dy.MLabel('导出选项'), self.export_type_rb, self.save_ext_cb, stretch=True)
        self.add_widgets_h_line(self.tips_label)
        self.add_widgets_h_line(self.run_bt)

    def adjust_ui(self):
        self.export_type_rb.set_button_list(['分别输出', '拼成一整张'])
        self.export_type_rb.set_dayu_checked(0)
        self.clear_bt.setFixedWidth(130)
        self.save_ext_cb.set_menus(SUPPORTED_EXT[:5])

        self.model.set_header_list(HEADER_LIST)
        self.table_view.setModel(self.model)
        self.table_view.enable_context_menu(enable=True)

    def connect_command(self):
        self.table_view.fileDropped.connect(partial(self.drop_to_table_function))
        self.run_bt.clicked.connect(self.run_bt_clicked)
        self.clear_bt.clicked.connect(self.clear_bt_clicked)
        self.table_view.sig_context_menu.connect(self.slot_context_menu)
    
    def run_bt_clicked(self):
        if not check_depend_tool_exist():
            dy.MToast(text='请设置依赖软件路径',
                      duration=3.0,
                      dayu_type='error',
                      parent=self).show()
            return
        
        
        ext = self.save_ext_cb.text()
        if self.export_type_rb.get_dayu_checked() == 0:
            export_path = QtWidgets.QFileDialog.getExistingDirectory(parent=self,
                                                                    caption='选择一个目录')
        elif self.export_type_rb.get_dayu_checked() == 1:
            export_path, _ = QtWidgets.QFileDialog.getSaveFileName(parent=self,
                                                                   caption='导出整个图片',
                                                                   filter=f'图片 (*{" *".join(SUPPORTED_EXT[:5])})')
        else:
            return
        
        if not export_path:
            return
            
        self.set_ui_status(freezed=True)
        task = AddTextTask(data_list=self.model.get_data_list(),
                           output_path=export_path,
                           ext=ext,
                           export_type_num=self.export_type_rb.get_dayu_checked(),
                           parent=self)
        task.log_sig.connect(self.tips_label.setText)
        task.finished.connect(self.set_ui_status)
        task.start()

    def clear_bt_clicked(self):
        self.model.clear()
        self.table_view.resizeColumnsToContents()
        self.table_view.resizeRowsToContents()
    
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

    def slot_context_menu(self, data):
        if not data.selection:
            return
        selections = data.selection
        if selections:
            self.create_context_menu(selections=selections)
    
    def create_context_menu(self, selections):
        menu = dy.MMenu(parent=self.table_view)
        menu.addAction('编辑文字', partial(self.edit_text, selections))
        menu.addAction('从表格中删除', partial(self.remove_item, selections))
        menu.exec_(QtGui.QCursor.pos())
    
    def edit_text(self, selections):
        dialog = EditTextDialog(parent=self)
        if dialog.exec_():
            for data in selections:
                data['text'] = dialog.current_text
                data['color'] = dialog.current_color
                data['size'] = dialog.current_size
                self.table_view.resizeColumnsToContents()
                self.table_view.resizeRowsToContents()

    def remove_item(self, selections):
        for sel in selections:
            self.model.remove(sel)

        self.table_view.resizeColumnsToContents()
        self.table_view.resizeRowsToContents()
    
    def set_ui_status(self, freezed=False):
        for w in (self.save_ext_cb, self.export_type_rb, self.run_bt):
            w.setEnabled(not freezed)


class EditTextDialog(CommonDialog):
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.current_color = QtGui.QColor('#aa0000')

        self.text_cb = MenuPushButton().small()
        self.text_line = dy.MLineEdit().small()
        self.color_choose_bt = dy.MPushButton().small()
        self.apply_bt = dy.MPushButton('应用').small().primary()
        self.cancel_bt = dy.MPushButton('取消').small()
        self.text_size_box = dy.MSpinBox().small()

        self.init_ui()
        self.adjust_ui()
        self.connect_command()
    
    def init_ui(self):
        self.add_widgets_h_line(dy.MLabel('文字'), self.text_cb, self.text_line)
        self.add_widgets_h_line(dy.MLabel('颜色'), self.color_choose_bt, stretch=True)
        self.add_widgets_h_line(dy.MLabel('文字大小'), self.text_size_box, stretch=True)
        self.add_widgets_h_line(self.apply_bt, self.cancel_bt)
        self.setLayout(self.main_layout)

    def adjust_ui(self):
        self.text_size_box.setRange(1, 100)
        self.text_size_box.setValue(16)
        self.text_size_box.setFixedWidth(100)
        self.text_cb.set_menus(['制作中', '待审核', '已进序列', '自定义'])
        self.text_cb.setFixedWidth(100)
        self.color_choose_bt.setFixedWidth(100)
        self.color_choose_bt.setStyleSheet(f'background-color: {self.current_color.name()};')
        self.text_line.setEnabled(False)

        self.setWindowTitle('编辑文字')
        self.resize(480, 150)
    
    def connect_command(self):
        self.apply_bt.clicked.connect(self.accept)
        self.cancel_bt.clicked.connect(self.reject)
        self.color_choose_bt.clicked.connect(self.color_choose_bt_clicked)
        self.text_cb.menu_selected_signal.connect(self.text_cb_clicked)
    
    def color_choose_bt_clicked(self):
        color = QtWidgets.QColorDialog.getColor(parent=self)
        if color.isValid():
            self.color_choose_bt.setStyleSheet(f'background-color: {color.name()};')
            self.current_color = color
    
    def text_cb_clicked(self, text):
        if text == '自定义':
            self.text_line.setEnabled(True)
        else:
            self.text_line.setEnabled(False)
    
    @property
    def current_text(self):
        if self.text_cb.text() == '自定义':
            return self.text_line.text()
        else:
            return self.text_cb.text()
    
    @property
    def current_size(self):
        return self.text_size_box.value()


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
                'image': thumb_path,
                'text': '',
                'color': QtGui.QColor('#aa0000'),
                'size': 10
            }
            self.data_sig.emit(data)


class AddTextTask(QtCore.QThread):

    log_sig = QtCore.Signal(str)

    def __init__(self, data_list, output_path, ext, export_type_num, parent=None):
        super().__init__(parent=parent)

        self.data_list = data_list
        self.output_path = output_path
        self.ext = ext
        self.export_type_num = export_type_num

    def run(self):
        current = 0
        total = len(self.data_list)
        output_files = []

        if self.export_type_num == 0:
            temp_output_path = self.output_path
        else:
            temp_output_path = tempfile.mkdtemp()

        for data in self.data_list:
            file_name = os.path.splitext(data['file_name'])[0]
            output_image_file = os.path.join(temp_output_path, f'{file_name}{self.ext}')
            output_files.append(output_image_file)
            color = data['color']
            rgb = f'rgb({color.red()}, {color.green()}, {color.blue()})'
            run_add_text_to_image(image_file=data['file_path'],
                                  output_image_file=output_image_file,
                                  text=data['text'],
                                  color=rgb,
                                  size=data['size']*10)

            current += 1
            self.log_sig.emit(f'({current}/{total}) 导出文件: {output_image_file}')
        
        if self.export_type_num == 1:
            vertical_count, horizontal_count = self.calc_vh_value(total_count=len(output_files))
            run_collage_images(image_files=output_files,
                               output_image_file=self.output_path,
                               vertical_count=vertical_count,
                               horizontal_count=horizontal_count)
            logger.debug(f'删除临时文件夹: {temp_output_path}')
            shutil.rmtree(temp_output_path)

        self.log_sig.emit('导出完成!')
    
    @staticmethod
    def calc_vh_value(total_count):
        horizontal_count = int(total_count ** 0.5)
        if horizontal_count * horizontal_count < total_count:
            horizontal_count += 1
        vertical_count = horizontal_count

        return horizontal_count, vertical_count

