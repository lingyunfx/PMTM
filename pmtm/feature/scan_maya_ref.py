import os
import csv
import traceback

import dayu_widgets as dy
from PySide2 import QtWidgets, QtCore

from pmtm.common_widgets import CommonToolWidget, CommonDialog, CommonWidget, InfoBoard, message_box, question_box
from pmtm.core import logger
from pmtm.helper import scan_files



class MayaRefScanUI(CommonToolWidget):
    """
    功能主界面
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # data
        self.replace_map_list = []  # 被替换的前后引用文件路径列表 [{'old_path': 'new_path'}, {'old_path': 'new_path'}, ...]
        self.maya_files = {}  # 扫描到的maya文件 {file_path: [ref_path1, ref_path2, ...]}
        self.replace_one_time = False  # 记录是否执行过替换，如果执行过，需再次扫描重置该值。

        # widgets
        self.scan_path_line = dy.MLineEdit().folder().small()
        self.tab = dy.MLineTabWidget(alignment=QtCore.Qt.AlignLeft)
        self.ref_list_widget = MayaRefListWidget(parent=self)
        self.maya_tree_widget = MayaFileTreeWidget(parent=self)
        self.scan_bt = dy.MPushButton('扫描').small().primary()
        self.replace_bt = dy.MPushButton('执行替换').small().primary()
        self.export_bt = dy.MPushButton('导出csv表格').small().primary()
        self.include_ck = dy.MCheckBox('包含子目录')
        self.info_board = InfoBoard(parent=self)
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, parent=self)

        self.setup()

    def init_ui(self):
        self.tab.add_tab(self.ref_list_widget, 'Reference文件列表')
        self.tab.add_tab(self.maya_tree_widget, 'Maya文件树')
        self.splitter.addWidget(self.tab)
        self.splitter.addWidget(self.info_board)
        
        self.add_widgets_h_line(dy.MLabel('路径'), self.scan_path_line, self.scan_bt, self.include_ck)
        self.add_widgets_h_line(self.splitter)
        self.add_widgets_h_line(self.export_bt, self.replace_bt)

    def adjust_ui(self):
        self.maya_tree_widget.tree.setColumnCount(1)
        self.maya_tree_widget.tree.setHeaderHidden(True)
        self.maya_tree_widget.tree.setSelectionMode(QtWidgets.QTreeWidget.ExtendedSelection)
        self.tab.tool_button_group.set_dayu_checked(0)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 3)

    def connect_command(self):
        self.scan_bt.clicked.connect(self.scan_bt_clicked)
        self.export_bt.clicked.connect(self.export_bt_clicked)
        self.replace_bt.clicked.connect(self.replace_bt_clicked)
        self.ref_list_widget.list.itemDoubleClicked.connect(self.double_click_ref_file)
        self.ref_list_widget.switch_ori_bt.clicked.connect(self.switch_ori_bt_clicked)
        self.ref_list_widget.reset_bt.clicked.connect(self.reset_bt_clicked)
        self.maya_tree_widget.search_line.textChanged.connect(self.update_maya_tree)
        self.maya_tree_widget.extend_bt.clicked.connect(self.maya_tree_widget.tree.expandAll)
        self.maya_tree_widget.collapse_bt.clicked.connect(self.maya_tree_widget.tree.collapseAll)

    def scan_bt_clicked(self):
        # 检查
        scan_folder = self.scan_path_line.text()
        if not scan_folder or not os.path.isdir(scan_folder):
            dy.MToast(text='路径不存在!',
                      dayu_type='error',
                      duration=3.0,
                      parent=self).show()
            return
        
        # 清空所有已有的数据
        self.replace_one_time = False
        self.replace_map_list.clear()
        self.maya_files.clear()
        self.ref_list_widget.list.clear()
        self.maya_tree_widget.tree.clear()

        # 设置工具状态
        self.set_tool_status(status=False)

        # 打印日志
        logger.debug('点击扫描按钮')
        logger.debug(f'扫描路径: {self.scan_path_line.text()}')
        logger.debug(f'包含子目录: {self.include_ck.isChecked()}')

        # 创建任务
        task = ScanReferenceTask(scan_folder=self.scan_path_line.text(),
                                     is_include=self.include_ck.isChecked(),
                                     parent=self)
        task.msg_sig.connect(self.info_board.add_line)
        task.ref_path_sig.connect(self.ref_list_widget.list.addItem)
        task.ref_path_sig.connect(lambda x: self.replace_map_list.append({'old_path': x, 'new_path': x}))
        task.maya_files_sig.connect(self.maya_files.update)
        task.finished.connect(self.set_tool_status)
        task.finished.connect(self.update_maya_tree)
        task.start()
    
    def search_line_text_changed(self):
        """
        搜索框文本改变时, 更新maya文件树
        """
        self.maya_tree_widget.search_line.textChanged.connect(self.update_maya_tree)
    
    def export_bt_clicked(self):
        """
        导出csv表格
        """
        export_file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Export csv', '', 'CSV Files(*.csv)')
        if not export_file_path:
            return
        
        csv_list = [['Maya file', 'Reference']]

        for ma_file, ref_list in self.maya_files.items():
            for ref in ref_list:
                csv_list.append([ma_file, ref])

        with open(export_file_path, 'w', newline='') as f:
            csv_write = csv.writer(f)
            for row in csv_list:
                csv_write.writerow(row)
        
        self.info_board.add_line(text=f'导出位置: {export_file_path}')

        dy.MToast(text='导出完成',
                  dayu_type='success',
                  duration=3.0,
                  parent=self).show()
    
    def replace_bt_clicked(self):
        if self.replace_one_time:
            message_box(text='为防止重复替换，请先点击"扫描"按钮，重置当前数据。',
                        success=False,
                        parent=self)
            return
        
        if not question_box(text='确定要执行替换操作吗？\n\n(注意:该操作会覆盖原始文件, 替换前请备份！)',
                           parent=self):
            return

        self.replace_one_time = True

        # 打印日志
        logger.debug('点击执行替换')
        logger.debug(f'maya_files: {self.maya_files}')
        logger.debug(f'replace_map_list: {self.replace_map_list}')

        # 设置工具状态
        self.set_tool_status(status=False)

        # 创建任务
        task = ReplacePathTask(maya_files=self.maya_files,
                               replace_map_list=self.replace_map_list,
                               parent=self)
        task.msg_sig.connect(self.info_board.add_line)
        task.finished.connect(self.set_tool_status)
        task.start()
    
    def reset_bt_clicked(self):
        """
        将所有引用文件的路径重置为原始路径
        """
        for num, item in enumerate(self.replace_map_list):
            item['new_path'] = item['old_path']
            self.ref_list_widget.list.item(num).setText(item['old_path'])
    
    def double_click_ref_file(self, item):
        """
        双击引用文件列表中的文件，弹出替换路径对话框
        """
        if self.ref_list_widget.switch_ori_bt.isChecked():
            self.info_board.add_line('以防止混淆, 请取消勾选"显示原始路径"',
                                     typ='error')
            return

        index_num = self.ref_list_widget.list.currentRow()
        old_path = self.replace_map_list[index_num]['old_path']
        new_path = self.replace_map_list[index_num]['new_path']

        dialog = ReplacePathDialog(old_path=old_path,
                                   new_path=new_path,
                                   parent=self)
        if dialog.exec_():
            new_path = dialog.new_path_line.text().replace('\\', '/')
            file_name = os.path.basename(old_path)
            
            if not os.path.isfile(new_path):
                return self.info_board.add_line('新路径不存在，请重新选择')

            if old_path == new_path:
                self.info_board.add_line('旧路径与新路径相同，不做更改')
                return

            if dialog.match_name_ck.isChecked():
                for i in range(len(self.replace_map_list)):
                    if file_name == os.path.basename(self.replace_map_list[i]['old_path']):
                        self.replace_map_list[i]['new_path'] = new_path
                        item = self.ref_list_widget.list.item(i)
                        item.setText(f'*{new_path}')
            else:
                self.replace_map_list[index_num]['new_path'] = new_path
                item = self.ref_list_widget.list.item(index_num)
                item.setText(f'*{new_path}')
    
    def switch_ori_bt_clicked(self):
        """
        切换显示原始路径和替换路径
        """
        for num, item in enumerate(self.replace_map_list):
            if item['old_path'] == item['new_path']:
                continue
            if self.ref_list_widget.switch_ori_bt.isChecked():
                self.ref_list_widget.list.item(num).setText(item['old_path'])
            else:
                self.ref_list_widget.list.item(num).setText(f'*{item["new_path"]}')

    def update_maya_tree(self):
        """
        扫描完成后, 更新maya文件树
        """
        self.maya_tree_widget.tree.clear()
        keyword = self.maya_tree_widget.search_line.text()
        for file_path, ref_paths in self.maya_files.items():
            file_name = os.path.basename(file_path)
            if keyword and keyword not in file_name:
                continue
            
            item = QtWidgets.QTreeWidgetItem([file_path])
            self.maya_tree_widget.tree.addTopLevelItem(item)
            for ref_path in ref_paths:
                item.addChild(QtWidgets.QTreeWidgetItem([ref_path]))
    
    def set_tool_status(self, status=True):
        """
        当任务执行时, 禁用工具按钮
        """
        widgets = [self.scan_path_line, self.scan_bt, self.include_ck, self.ref_list_widget.switch_ori_bt,
                   self.ref_list_widget.reset_bt, self.maya_tree_widget.extend_bt, self.maya_tree_widget.collapse_bt,
                   self.export_bt, self.replace_bt]
        for widget in widgets:
            widget.setDisabled(not status)


class MayaRefListWidget(CommonWidget):
    """
    显示maya引用文件列表组件
    """
    def __init__(self, parent=None):
        super(MayaRefListWidget, self).__init__(parent=parent)

        self.list = QtWidgets.QListWidget()
        self.switch_ori_bt = dy.MCheckBox('显示原始路径')
        self.reset_bt = dy.MPushButton('重置').small()
        
        self.init_ui()
        self.adjust_ui()
    
    def init_ui(self):
        self.add_widgets_h_line(self.switch_ori_bt, self.reset_bt, stretch=1)
        self.add_widgets_h_line(self.list)
        self.setLayout(self.main_layout)
    
    def adjust_ui(self):
        self.switch_ori_bt.setFixedWidth(100)
        self.reset_bt.setFixedWidth(80)
        self.main_layout.setContentsMargins(0, 3, 0, 3)


class MayaFileTreeWidget(CommonWidget):
    """
    显示maya文件树组件
    """

    def __init__(self, parent=None):
        super(MayaFileTreeWidget, self).__init__(parent=parent)

        self.extend_bt = dy.MPushButton('展开所有').small()
        self.collapse_bt = dy.MPushButton('收起所有').small()
        self.search_line = dy.MLineEdit().search().small()
        self.tree = QtWidgets.QTreeWidget()

        self.init_ui()
        self.adjust_ui()

    def init_ui(self):
        self.add_widgets_h_line(dy.MLabel('搜索Maya文件'), self.search_line,
                                self.extend_bt, self.collapse_bt, stretch=True)
        self.add_widgets_h_line(self.tree)
        self.setLayout(self.main_layout)
        self.search_line.setFixedWidth(200)
    
    def adjust_ui(self):
        self.main_layout.setContentsMargins(0, 3, 0, 3)


class ReplacePathDialog(CommonDialog):
    """
    替换路径对话框
    """
    def __init__(self, old_path, new_path, parent=None):
        super(ReplacePathDialog, self).__init__(parent=parent)

        # data
        self.old_path = old_path
        self.new_path = new_path

        # widgets
        self.old_path_line = dy.MLineEdit(self.old_path).small()
        self.new_path_line = dy.MLineEdit(self.new_path).small().file(filters=['*.ma', '*.mb'])
        self.match_name_ck = dy.MCheckBox('匹配相同文件名的路径')
        self.apply_bt = dy.MPushButton('应用').small().primary()
        self.cancel_bt = dy.MPushButton('取消').small()

        self.init_ui()
        self.adjust_ui()
        self.connect_command()
    
    def init_ui(self):
        self.add_widgets_h_line(dy.MLabel('旧路径'), self.old_path_line)
        self.add_widgets_h_line(dy.MLabel('新路径'), self.new_path_line)
        self.add_widgets_h_line(self.match_name_ck)
        self.add_widgets_h_line(self.apply_bt, self.cancel_bt)
        self.setLayout(self.main_layout)
    
    def adjust_ui(self):
        self.old_path_line.setEnabled(False)
        self.old_path_line.setMinimumWidth(400)
        self.new_path_line.setMinimumWidth(400)
        self.setWindowTitle('替换路径对话框')
    
    def connect_command(self):
        self.apply_bt.clicked.connect(self.accept)
        self.cancel_bt.clicked.connect(self.reject)


class ScanReferenceTask(QtCore.QThread):
    """
    扫描maya引用文件任务
    """

    msg_sig = QtCore.Signal(str)
    ref_path_sig = QtCore.Signal(str)
    maya_files_sig = QtCore.Signal(dict)

    def __init__(self, scan_folder, is_include, parent=None):
        super(ScanReferenceTask, self).__init__(parent=parent)
        
        # params
        self.scan_folder = scan_folder
        self.is_include = is_include

        # data
        self.maya_files = {}

    def run(self):
        files_list = scan_files(scan_folder=self.scan_folder,
                                is_include=self.is_include,
                                ext_list=['.ma'])
        
        # 扫描文件
        for count, file_path in enumerate(files_list, start=1):
            self.maya_files.setdefault(file_path, [])
            self.msg_sig.emit(f'({count}/{len(files_list)}) 扫描文件: {file_path}')
            self.get_maya_reference(file_path)
        
        # 扫描完成，打印日志
        result_maya_count = len(self.maya_files)
        result_ref_count = len(set(ref_path for ref_list in self.maya_files.values() for ref_path in ref_list))

        self.msg_sig.emit(f'[pass]扫描完成，共有{result_maya_count}个maya文件，{result_ref_count}个引用文件')
        self.maya_files_sig.emit(self.maya_files)

    def get_maya_reference(self, file_path):
        """
        获取maya文件的引用文件
        """
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
            self.msg_sig.emit(f'[error]处理文件时出现编码错误 {file_path}，请查看日志')
            return

        # 读取文件内容, 获取reference路径
        for line in content:
            line = line.strip()

            if not line or line[-5:-2] not in ('.ma', '.mb'):
                continue

            if '-rfn' in line:
                line = line.split()[-1]

            if '"mayaAscii"' in line:
                line = line.split('"mayaAscii"')[-1].strip()
            
            if '"mayaBinary"' in line:
                line = line.split('"mayaBinary"')[-1].strip()
            
            if line.startswith('"') and line.endswith(';'):
                ref_path = line.replace('"', '')
                ref_path = ref_path.replace(';', '')

                if ref_path not in self.maya_files[file_path]:
                    self.maya_files[file_path].append(ref_path)
                    self.msg_sig.emit(f' -  [引用] {ref_path}')
                    self.ref_path_sig.emit(ref_path)


class ReplacePathTask(QtCore.QThread):

    """
    执行实际替换的任务类
    """

    msg_sig = QtCore.Signal(str)

    def __init__(self, maya_files, replace_map_list, parent=None):
        super(ReplacePathTask, self).__init__(parent=parent)

        # UI data
        self.maya_files = maya_files
        self.replace_map_list = replace_map_list

        # 过滤出需要替换的路径，存储为字典。key为旧路径，value为新路径
        self.replace_path_map_dict = {i.get('old_path'): i.get('new_path')
                                      for i in self.replace_map_list 
                                      if i.get('old_path') != i.get('new_path')}

    def run(self):
        num = 0
        total = len(self.maya_files)

        try:
            for f, ref_path_list in self.maya_files.items():
                num += 1
                self.msg_sig.emit(f'({num}/{total}) 执行替换操作...')

                if self.is_read_only(f):
                    self.msg_sig.emit(f'[error][只读文件] - {f}')
                elif not ref_path_list:
                    self.msg_sig.emit(f'[跳过，没有任何引用] - {f}')
                elif not self.check_need_replace(f):
                    self.msg_sig.emit(f'[跳过，不需要替换] - {f}')
                else:
                    self.do_replace(f)  # 执行实际替换操作
                    self.msg_sig.emit(f'[已替换] - {f}')
        except Exception as e:
            logger.error(f'替换任务执行失败，请查看日志获取详细信息')
            logger.error(f'{traceback.format_exc()}')
            return

        self.msg_sig.emit('[pass]替换任务完成!')

    def do_replace(self, f):
        """
        执行替换操作
        """
        bak_f = f[:-3] + '_bak.ma'
        with open(bak_f, 'w') as new_data:
            logger.debug(f'创建备份文件 {bak_f}')
            with open(f, 'r') as old_data:
                for line in old_data.readlines():
                    line = self.replace_if_reference_line(line)
                    new_data.writelines(line)
        logger.debug(f'删除原文件 {f}')
        os.remove(f)
        logger.debug(f'重命名备份文件 {bak_f} 为 {f}')
        os.rename(bak_f, f)

    def replace_if_reference_line(self, line):
        """
        如果行是引用行，则替换路径
        """
        for old_path, new_path in self.replace_path_map_dict.items():
            if old_path in line:
                # 替换路径
                line = line.replace(old_path, new_path)
                # 如果旧路径和新路径的扩展名不同，则需要替换文件格式
                old_ext = os.path.splitext(old_path)[1]
                new_ext = os.path.splitext(new_path)[1]
                if old_ext != new_ext:
                    if new_ext == '.ma':
                        line = line.replace('"mayaBinary"', '"mayaAscii"')
                    elif new_ext == '.mb':
                        line = line.replace('"mayaAscii"', '"mayaBinary"')
        return line

    def check_need_replace(self, file_path):
        """
        检查该文件是否需要替换，如果需要返回True，否则返回False。
        """
        if file_path not in self.maya_files:
            return False
        
        for ref_path in self.maya_files[file_path]:
            if ref_path in self.replace_path_map_dict:
                return True
        return False

    @staticmethod
    def is_read_only(f):
        return True if os.stat(f).st_mode == 33060 else False
