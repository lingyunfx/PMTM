import os
import time
import json
import tempfile
import copy
import traceback
from functools import partial

import dayu_widgets as dy
from dayu_widgets.drawer import MDrawer
from dayu_path import DayuPath
from PySide2 import QtWidgets, QtCore, QtGui

from pmtm.helper import g_pixmap, check_depend_tool_exist, open_file, open_folder
from pmtm.core import logger, user_setting
from pmtm.common_widgets import CommonToolWidget, MenuPushButton, CommonDialog, DropTabelView, InfoBoard, CommonWidget
from pmtm.media_utils import extract_thumbnail_from_image, run_add_text_to_image, run_add_text_to_collage_image


def _color(x, y):
    return QtGui.QColor(y.get('color'))


SUPPORTED_EXT = ['.png', '.jpg', '.jpeg', '.tiff', '.exr', '.JPG', '.JPEG', '.TIFF', '.EXR', '.PNG']

HEADER_LIST = [
            {'label': '缩略图', 'key': 'thumbnail', 'icon': g_pixmap},
            {'label': '文件名', 'key': 'file_name', 'align': 'center'},
            {'label': '文字', 'key': 'text', 'color': _color, 'align': 'center', 'editable': True},
            {'label': '拼图排序', 'key': 'order', 'align': 'center'},
            {'label': '文件路径', 'key': 'file_path'}
        ]

GRAVITY_DICT = {
    '左上角': 'NorthWest',
    '上中': 'North',
    '右上角': 'NorthEast',
    '左中': 'West',
    '中中': 'Center',
    '右中': 'East',
    '左下角': 'SouthWest',
    '下中': 'South',
    '右下角': 'SouthEast',
}

DEFAULT_GRAVITY = '下中'
DEFAULT_COLOR = '#aa0000'
DEFAULT_SIZE = 6


class AddTextToImageUI(CommonToolWidget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # data
        self.model = dy.MTableModel()
        self.sort_model = dy.MSortFilterModel()

        # widgets
        self.table_view = DropTabelView(show_row_count=True, parent=self)
        self.info_board = InfoBoard(parent=self)
        self.splitter = QtWidgets.QSplitter(orientation=QtCore.Qt.Vertical, parent=self)
        self.clear_bt = dy.MPushButton('清空所有').small()
        self.is_include_ck = dy.MCheckBox('包含子目录')
        self.only_get_first_ck = dy.MCheckBox('序列帧只取第一帧')
        self.save_history_ck = dy.MCheckBox('保存历史记录')
        self.sort_by_file_name_ck = dy.MCheckBox('按文件名排序')
        self.history_bt = dy.MPushButton('查看历史记录').small()
        self.history_line = dy.MLineEdit().small()
        self.open_after_export_ck = dy.MCheckBox('导出后打开')
        self.run_bt = dy.MPushButton('开始任务').small().primary()
        self.export_type_rb = dy.MRadioButtonGroup()
        self.gravity_rb = dy.MRadioButtonGroup()
        self.text_size_box = dy.MSpinBox().small()
        self.text_transparency_box = dy.MSpinBox().small()
        self.save_ext_cb = QtWidgets.QComboBox()
        self.gamma_box = dy.MDoubleSpinBox().small()

        self.setup()

    def init_ui(self):
        self.splitter.addWidget(self.table_view)
        self.splitter.addWidget(self.info_board)

        self.add_widgets_h_line(dy.MLabel('扫描选项'), self.is_include_ck, self.only_get_first_ck, self.sort_by_file_name_ck,
                                self.history_bt,dy.MLabel('Gamma'), self.gamma_box,
                                dy.MLabel('针对exr格式文件，影响输出和输入').secondary(), stretch=True).addWidget(self.clear_bt)
        self.add_widgets_v_line(self.splitter)
        self.add_widgets_h_line(dy.MLabel('导出方式'), self.export_type_rb, stretch=True)
        self.add_widgets_h_line(dy.MLabel('文字设置'), dy.MLabel('大小'), self.text_size_box, dy.MLabel('透明度'), self.text_transparency_box,
                                dy.MDivider(orientation=QtCore.Qt.Vertical), dy.MLabel('对齐方式'), self.gravity_rb, stretch=True)
        self.add_widgets_h_line(dy.MLabel('输出格式'), self.save_ext_cb, self.open_after_export_ck, self.save_history_ck, self.history_line, stretch=True)
        self.add_widgets_h_line(self.run_bt)

    def adjust_ui(self):
        # 设置分割器比例
        self.splitter.setStretchFactor(0, 8)
        self.splitter.setStretchFactor(1, 2)

        # 设置导出选项
        self.export_type_rb.set_button_list(['分别输出', '拼成整张'])
        self.export_type_rb.set_dayu_checked(1)
        self.gravity_rb.set_button_list(list(GRAVITY_DICT.keys()))
        self.gravity_rb.set_dayu_checked(7)
        self.save_ext_cb.addItems(SUPPORTED_EXT[:5])
        self.text_size_box.setRange(1, 100)
        self.text_size_box.setValue(DEFAULT_SIZE)
        self.text_transparency_box.setRange(1, 100)
        self.text_transparency_box.setValue(100)
        self.text_transparency_box.setSuffix('%')
        self.gamma_box.setRange(0.1, 10)
        self.gamma_box.setSingleStep(0.1)
        self.gamma_box.setValue(float(user_setting.get('add_text_to_image_gamma', 1.0)))
        self.history_line.setPlaceholderText('在此输入历史记录名称')

        # 设置宽度
        self.history_line.setFixedWidth(180)
        self.gamma_box.setFixedWidth(90)
        self.text_transparency_box.setFixedWidth(80)
        self.text_size_box.setFixedWidth(60)
        self.save_ext_cb.setFixedWidth(100)
        self.clear_bt.setFixedWidth(130)
        self.is_include_ck.setFixedWidth(90)
        self.only_get_first_ck.setFixedWidth(120)

        # 设置勾选框默认值
        for w in (self.is_include_ck, self.only_get_first_ck, self.save_history_ck,
                  self.sort_by_file_name_ck, self.open_after_export_ck):
            w.setChecked(True)

        # 设置表格
        self.model.set_header_list(HEADER_LIST)
        self.sort_model.setSourceModel(self.model)
        self.table_view.setModel(self.sort_model)
        self.sort_model.set_header_list(HEADER_LIST)
        self.table_view.enable_context_menu(enable=True)

    def connect_command(self):
        self.table_view.fileDropped.connect(partial(self.drop_to_table_function))
        self.run_bt.clicked.connect(self.run_bt_clicked)
        self.clear_bt.clicked.connect(self.clear_bt_clicked)
        self.table_view.sig_context_menu.connect(self.slot_context_menu)
        self.history_bt.clicked.connect(self.history_bt_clicked)
        self.gamma_box.valueChanged.connect(self.gamma_box_value_changed)
        self.save_history_ck.stateChanged.connect(self.save_history_ck_state_changed)
    
    def run_bt_clicked(self):
        logger.debug(f'开始任务按钮点击')

        # 检查依赖软件是否存在
        if not check_depend_tool_exist():
            dy.MToast(text='请设置依赖软件路径',
                      duration=3.0,
                      dayu_type='error',
                      parent=self).show()
            return

        # 获取导出路径
        if self.export_type_rb.get_dayu_checked() == 0:
            export_path = QtWidgets.QFileDialog.getExistingDirectory(parent=self,
                                                                    caption='选择目录')
        elif self.export_type_rb.get_dayu_checked() == 1:
            export_path, _ = QtWidgets.QFileDialog.getSaveFileName(parent=self,
                                                                   caption='保存为图片',
                                                                   filter=f'图片 (*{" *".join(SUPPORTED_EXT[:5])})')
        else:
            return
        
        if not export_path:
            return
        
        logger.debug(f'导出路径: {export_path}')

        # 只保留必要数据
        data_list = copy.deepcopy(self.model.get_data_list())
        data_list = [{'file_path': data['file_path'],
                      'text': data['text'],
                      'color': data['color'],
                      'order': data['order'],
                      'thumbnail': data['thumbnail'],
                      'file_name': data['file_name'],
                      'image': data['image']
                      } 
                      for data in data_list]
        logger.debug(f'数据列表: {data_list}')

        # 保存历史记录
        if self.save_history_ck.isChecked():
            history_folder = self.get_history_folder()
            if self.history_line.text():
                file_name = self.history_line.text()
            else:
                file_name = f'{time.strftime("%Y-%m-%d_%H-%M-%S")}'
            history_file = os.path.join(history_folder, file_name)
            with open(f'{history_file}.json', 'w') as f:
                json.dump(data_list, f)
            logger.debug(f'保存历史记录: {history_file}.json')

        # 开始任务
        self.set_ui_status(freezed=True)
        task = AddTextTask(data_list=data_list,
                           output_path=export_path,
                           ext=self.save_ext_cb.currentText(),
                           export_type_num=self.export_type_rb.get_dayu_checked(),
                           open_after_export=self.open_after_export_ck.isChecked(),
                           gravity=self.current_gravity,
                           text_size=self.text_size_box.value(),
                           text_transparency=self.text_transparency_box.value(),
                           gamma=self.gamma_box.value(),
                           parent=self)
        task.log_sig.connect(self.info_board.add_line)
        task.finished.connect(self.set_ui_status)
        task.start()

    def clear_bt_clicked(self):
        """
        清空表格
        """
        self.model.clear()
        self.table_view.resizeColumnsToContents()
        self.table_view.resizeRowsToContents()
    
    def drop_to_table_function(self, path_list):
        """
        获取拖拽到表格的路径列表，进行处理
        """
        logger.debug(f'拖拽到表格的路径列表: {path_list}')
        if not check_depend_tool_exist():
            dy.MToast(text='请设置依赖软件路径',
                      duration=3.0,
                      dayu_type='error',
                      parent=self).show()
            return

        self.set_ui_status(freezed=True)
        task = DropImageTask(path_list=path_list,
                             is_include=self.is_include_ck.isChecked(),
                             only_get_first=self.only_get_first_ck.isChecked(),
                             sort_by_file_name=self.sort_by_file_name_ck.isChecked(),
                             gamma=self.gamma_box.value(),
                             parent=self)
        task.data_sig.connect(self.add_data_to_table)
        task.finished.connect(self.set_ui_status)
        task.start()
    
    def add_data_to_table(self, data):
        """
        将数据添加到表格中
        """
        # 检查文件是否存在
        exists_path_list = [x['file_path'] for x in self.model.get_data_list()]
        if data['file_path'] in exists_path_list:
            dy.MToast(text='文件已存在',
                      duration=3.0,
                      dayu_type='error',
                      parent=self).show()
            return

        # 如果勾选按文件名排序，则进行排序
        if self.sort_by_file_name_ck.isChecked():
            self.model.append(data)
            self.sort_by_file_name()
        else:
            data.update({'order': self.model.rowCount() + 1})
            self.model.append(data)

        # 调整表格大小
        self.table_view.resizeColumnsToContents()
        self.table_view.resizeRowsToContents()

    def slot_context_menu(self, data):
        """
        右键菜单
        """
        if not data.selection:
            return
        selections = data.selection
        if selections:
            self.create_context_menu(selections=selections)
    
    def create_context_menu(self, selections):
        """
        创建右键菜单
        """
        menu = dy.MMenu(parent=self.table_view)
        menu.addAction('编辑文字', partial(self.edit_text, selections))
        menu.addAction('从表格中删除', partial(self.remove_item, selections))
        menu.addSeparator()
        menu.addAction('按文件名排序', partial(self.sort_by_file_name))
        menu.addAction('按选择顺序排序', partial(self.sort_by_selection, selections))
        menu.exec_(QtGui.QCursor.pos())
    
    def edit_text(self, selections):
        """
        右键菜单-编辑文字
        """
        dialog = EditTextDialog(parent=self)
        if dialog.exec_():
            for data in selections:
                data['text'] = dialog.current_text
                data['color'] = dialog.current_color
                self.table_view.resizeColumnsToContents()
                self.table_view.resizeRowsToContents()

    def remove_item(self, selections):
        """
        从表格中删除选中项
        """
        for sel in selections:
            self.model.remove(sel)

        if self.sort_by_file_name_ck.isChecked():
            self.sort_by_file_name()

        self.table_view.resizeColumnsToContents()
        self.table_view.resizeRowsToContents()
    
    def sort_by_selection(self, selections):
        """
        按选择顺序排序
        """
        data_list = self.model.get_data_list()
        self.model.clear()
        start_sort_num = len(selections)

        for data in data_list:
            if data in selections:
                data.update({'order': selections.index(data) + 1})
            else:
                start_sort_num += 1
                data.update({'order': start_sort_num})

        data_list = sorted(data_list, key=lambda x: x['order'])
        for data in data_list:
            self.model.append(data)

        self.table_view.resizeColumnsToContents()
        self.table_view.resizeRowsToContents()
    
    def sort_by_file_name(self):
        """
        按文件名排序
        """
        data_list = self.model.get_data_list()
        self.model.clear()

        data_list = sorted(data_list, key=lambda x: x['file_name'])
        sort_num = 1
        for data in data_list:
            data.update({'order': sort_num})
            self.model.append(data)
            sort_num +=1

        self.table_view.resizeColumnsToContents()
        self.table_view.resizeRowsToContents()
    
    def set_ui_status(self, freezed=False):
        """
        设置UI状态
        """
        for w in (self.save_ext_cb, self.export_type_rb, self.run_bt, self.history_bt, self.clear_bt,
                  self.is_include_ck, self.only_get_first_ck, self.sort_by_file_name_ck, self.save_history_ck,
                  self.open_after_export_ck, self.gamma_box):
            w.setEnabled(not freezed)
    
    def import_data_from_file(self, file_path):
        """
        从历史记录中导入数据
        """
        if not os.path.exists(file_path):
            dy.MToast(text='文件不存在',
                      duration=3.0,
                      dayu_type='error',
                      parent=self).show()
            return

        self.clear_bt_clicked()
        with open(file_path, 'r') as f:
            data_list = json.load(f)
        
        data_list = sorted(data_list, key=lambda x: x['order'])
        for data in data_list:
            if not os.path.exists(data['file_path']):
                self.info_board.add_line(f'文件不存在: {data["file_path"]}')
                continue
            if not os.path.exists(data['image']):
                self.info_board.add_line(f'缩略图丢失，提取缩略图: {data["file_path"]}')
                tmp_dir = tempfile.mkdtemp()
                thumb_path = os.path.join(tmp_dir, 'thumbnail.jpg')
                extract_thumbnail_from_image(image_file=data['file_path'],
                                             output_image_file=thumb_path,
                                             gamma=self.gamma_box.value())
                data['image'] = thumb_path

            self.add_data_to_table(data)

    def history_bt_clicked(self):
        """
        历史记录按钮点击
        """
        history_folder = self.get_history_folder()
        history_widget = HistoryWidget(history_folder=history_folder,
                                       parent=self)
        history_widget.file_path_sig.connect(self.import_data_from_file)

        drawer = MDrawer('历史记录', parent=self).right()
        drawer.set_widget(history_widget)
        drawer.setFixedWidth(350)
        drawer.show()
    
    @staticmethod
    def get_history_folder():
        """
        获取历史记录文件夹
        """
        history_path = os.path.join(os.path.expanduser('~'), '.pmtm', 'history', 'add_text_to_image')
        if not os.path.exists(history_path):
            os.makedirs(history_path)
        return history_path
    
    @property
    def current_gravity(self):
        """
        获取当前对齐方式
        """
        _index = self.gravity_rb.get_dayu_checked()
        key = list(GRAVITY_DICT.keys())[_index]
        return GRAVITY_DICT[key]

    def gamma_box_value_changed(self, value):
        """
        每次改变记录伽马值
        """
        user_setting.set('add_text_to_image_gamma', value)

    def save_history_ck_state_changed(self, state):
        if state == QtCore.Qt.Checked:
            self.history_line.setHidden(False)
        else:
            self.history_line.setHidden(True)


class EditTextDialog(CommonDialog):
    """
    编辑文字对话框
    """
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # data
        self.current_color = '#aa0000'

        # widgets
        self.text_cb = MenuPushButton().small()
        self.text_line = dy.MLineEdit().small()
        self.color_choose_bt = dy.MPushButton().small()
        self.apply_bt = dy.MPushButton('应用').small().primary()
        self.cancel_bt = dy.MPushButton('取消').small()

        self.init_ui()
        self.adjust_ui()
        self.connect_command()
    
    def init_ui(self):
        self.add_widgets_h_line(dy.MLabel('文字'), self.text_cb, self.text_line)
        self.add_widgets_h_line(dy.MLabel('颜色'), self.color_choose_bt, stretch=True)
        self.add_widgets_h_line(self.apply_bt, self.cancel_bt)
        self.setLayout(self.main_layout)

    def adjust_ui(self):
        self.text_cb.set_menus(['制作中', '待审核', '已进序列', '自定义'])
        self.text_cb.setFixedWidth(100)
        self.color_choose_bt.setFixedWidth(100)
        self.color_choose_bt.setStyleSheet(f'background-color: {QtGui.QColor(self.current_color).name()};')
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
            self.current_color = color.name()
    
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


class HistoryWidget(CommonWidget):

    file_path_sig = QtCore.Signal(str)

    def __init__(self, history_folder, parent=None):
        super().__init__(parent=parent)

        # data
        self.history_folder = history_folder
        self.history_files = {}

        # widgets
        self.list_widget = QtWidgets.QListWidget(parent=self)
        self.open_folder_bt = dy.MPushButton('打开历史记录文件夹').small()

        # init ui
        self.init_ui()
        self.set_data()
        self.connect_command()
    
    def init_ui(self):
        self.add_widgets_v_line(dy.MLabel('双击选择一项记录导入').h4().secondary(),
                                self.open_folder_bt, self.list_widget)
        self.setLayout(self.main_layout)
    
    def connect_command(self):
        self.list_widget.itemDoubleClicked.connect(self.list_widget_item_double_clicked)
        self.open_folder_bt.clicked.connect(self.open_folder_bt_clicked)
    
    def list_widget_item_double_clicked(self, item):
        self.file_path_sig.emit(self.history_files[item.text()])

    def set_data(self):
        # 过滤出所有json文件
        history_files_list = [os.path.join(self.history_folder, file) for file in os.listdir(self.history_folder) if file.endswith('.json')]
        # 按修改时间排序
        history_files_list = sorted(history_files_list, key=lambda x: os.path.getmtime(x), reverse=True)
        # 添加到列表中
        for history_file in history_files_list:
            name = os.path.splitext(os.path.basename(history_file))[0]
            self.list_widget.addItem(name)
            self.history_files[name] = history_file
    
    def open_folder_bt_clicked(self):
        open_folder(self.history_folder)


class DropImageTask(QtCore.QThread):
    """
    拖拽图片到表格中，获取图片信息任务类
    """

    data_sig = QtCore.Signal(dict)

    def __init__(self, path_list, is_include, only_get_first, sort_by_file_name=False, gamma=1.0, parent=None):
        super().__init__(parent=parent)

        self.path_list = path_list
        self.is_include = is_include
        self.only_get_first = only_get_first
        self.sort_by_file_name = sort_by_file_name
        self.gamma = gamma

    def run(self):
        try:
            # 获取所有文件
            files_list = self.get_all_file_path(self.path_list)

            # 如果勾选按文件名排序，则进行排序
            if self.sort_by_file_name:
                files_list = sorted(files_list, key=lambda x: os.path.basename(x))

            # 获取文件信息
            for file_path in files_list:
                logger.debug(f'获取文件信息: {file_path}')
                self.get_data_from_file(file_path)
        except Exception as e:
            logger.error(f'获取文件信息失败: {e}')
            logger.error(traceback.format_exc())

    def get_all_file_path(self, path_list):
        """
        从所有拖拽路径中，获取所有支持格式的文件路径
        """
        files_list = []

        for path in path_list:
            if os.path.isfile(path):
                if os.path.splitext(path)[1] in SUPPORTED_EXT:
                    files_list.append(path)
                else:
                    logger.error(f'不支持的文件类型: {path}')
                    continue
            elif os.path.isdir(path):
                root_folder = DayuPath(path)
                for seq_file in root_folder.scan(recursive=self.is_include, ext_filters=tuple(SUPPORTED_EXT)):
                    if self.only_get_first:
                        file_path = seq_file.restore_pattern(seq_file.frames[0])
                        files_list.append(file_path)
                    else:
                        for file_path in seq_file.restore_pattern(seq_file.frames):
                            files_list.append(file_path)
            else:
                continue

        return files_list


    def get_data_from_file(self, file_path):
        """
        从文件中获取数据
        """
        ext = os.path.splitext(file_path)[1]
        if ext not in SUPPORTED_EXT:
            logger.error(f'不支持的文件类型: {file_path}')
            return

        tmp_dir = tempfile.mkdtemp()
        thumb_path = os.path.join(tmp_dir, 'thumbnail.jpg')
        extract_thumbnail_from_image(image_file=file_path,
                                     output_image_file=thumb_path,
                                     gamma=self.gamma)
        
        data = {
            'thumbnail': '',
            'file_name': os.path.basename(file_path),
            'file_path': file_path,
            'image': thumb_path,
            'text': '',
            'color': DEFAULT_COLOR
        }
        self.data_sig.emit(data)


class AddTextTask(QtCore.QThread):
    """
    添加文字到图片任务类
    """

    log_sig = QtCore.Signal(str)

    def __init__(self, data_list, output_path, ext, export_type_num, open_after_export, gravity, text_size, text_transparency, gamma, parent=None):
        super().__init__(parent=parent)

        self.data_list = sorted(data_list, key=lambda x: x['order'])
        self.output_path = output_path
        self.ext = ext
        self.export_type_num = export_type_num
        self.open_after_export = open_after_export
        self.gravity = gravity
        self.text_size = text_size
        self.text_transparency = text_transparency
        self.gamma = gamma

    def run(self):
        try:
            if self.export_type_num == 0:
                # 导出方式：分别输出单张
                self.export_each_image(output_folder=self.output_path)
            elif self.export_type_num == 1:
                # 导出方式：输出整张。（为每张添加文字，然后拼成整张图）
                now_time = time.time()
                data_list = []

                for data in self.data_list:
                    color = QtGui.QColor(data['color'])
                    rgb = f'rgba({color.red()}, {color.green()}, {color.blue()}, {self.text_transparency/100.0})'
                    data_list.append({
                        'text': data['text'],
                        'color': rgb,
                        'file_path': data['file_path']
                    })

                # 计算水平和垂直数量，用于拼图
                vertical_count, horizontal_count = self.calc_vh_value(total_count=len(data_list))
                self.log_sig.emit(f'正在添加文字及拼图，请稍后...')

                # 执行主要函数
                run_add_text_to_collage_image(
                    output_image_file=self.output_path,
                    data_list=data_list,
                    horizontal_count=horizontal_count,
                    vertical_count=vertical_count,
                    gravity=self.gravity,
                    size=self.text_size*10,
                    gamma=self.gamma
                )
                self.log_sig.emit(f'添加文字及拼图完成，耗时: {time.time() - now_time:.2f}秒')
            else:
                return

            self.log_sig.emit(f'[pass]导出完成! {self.output_path}')

        except Exception as e:
            logger.error(f'导出失败: {e}')
            logger.error(traceback.format_exc())
            self.log_sig.emit(f'[error]导出失败，请查看日志。')

        if self.open_after_export:
            if os.path.isfile(self.output_path):
                open_file(self.output_path)
            elif os.path.isdir(self.output_path):
                open_folder(self.output_path)
            else:
                return
    
    def export_each_image(self, output_folder):
        """
        分别输出单张图片
        """
        output_files = []
        current = 0
        total = len(self.data_list)

        for data in self.data_list:
            file_name = os.path.splitext(data['file_name'])[0]
            output_image_file = os.path.join(output_folder, f'{file_name}{self.ext}')
            output_files.append(output_image_file)
            color = QtGui.QColor(data['color'])
            rgb = f'rgba({color.red()}, {color.green()}, {color.blue()}, {self.text_transparency/100.0})'
            run_add_text_to_image(image_file=data['file_path'],
                                  output_image_file=output_image_file,
                                  text=data['text'],
                                  color=rgb,
                                  size=self.text_size*10,
                                  gravity=self.gravity,
                                  gamma=self.gamma
                                  )

            current += 1
            self.log_sig.emit(f'({current}/{total}) 导出文件: {output_image_file}')
        return output_files
    
    @staticmethod
    def calc_vh_value(total_count):
        horizontal_count = int(total_count ** 0.5)
        if horizontal_count * horizontal_count < total_count:
            horizontal_count += 1
        vertical_count = horizontal_count

        return horizontal_count, vertical_count
