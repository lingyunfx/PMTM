import os
import traceback
import pymiere

import dayu_widgets as dy
from PySide2 import QtWidgets

from pmtm.core import logger
from pmtm.common_widgets import CommonToolWidget, InfoBoard


class PRToolsUI(CommonToolWidget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rename_bt = dy.MPushButton('执行批量命名').small().primary()
        self.check_rename_bt = dy.MPushButton('命名结果预测').small()
        self.rename_start_input = dy.MLineEdit().small()
        self.interval_num_box = dy.MSpinBox().small()
        self.export_split_bt = dy.MPushButton('执行批量导出').small().primary()
        self.export_dir_input = dy.MLineEdit().folder().small()
        self.presets_cb = QtWidgets.QComboBox()
        self.output_ext_cb = QtWidgets.QComboBox()
        self.info_broad = InfoBoard(parent=self)

        try:
            self.preset_dir = os.path.join(pymiere.objects.app.path, 'Settings', 'IngestPresets', 'Transcode')
            self.info_broad.add_line(f'从 {self.preset_dir} 获取到导出预设')
        except Exception as e:
            self.info_broad.add_line('[error]无法获取预设文件列表，请先打开Premiere Pro软件，再打开这个工具。')
            logger.error(e)
            self.preset_dir = ''

        self.setup()

    def init_ui(self):
        self.add_widgets_h_line(dy.MLabel('起始镜号'), self.rename_start_input,
                                dy.MLabel('间隔个数'), self.interval_num_box,
                                self.check_rename_bt, self.rename_bt, stretch=True)
        self.add_widgets_h_line(dy.MLabel('输出目录'), self.export_dir_input, self.presets_cb, self.output_ext_cb,
                                self.export_split_bt, stretch=True)
        self.add_widgets_v_line(self.info_broad)

    def adjust_ui(self):
        self.rename_start_input.setText('0010')
        self.interval_num_box.setValue(10)
        self.rename_start_input.setFixedWidth(100)
        self.interval_num_box.setFixedWidth(70)
        self.export_dir_input.setMinimumWidth(350)
        self.output_ext_cb.addItems(['mp4','mov'])

        if not self.preset_dir or not os.path.exists(self.preset_dir):
            self.presets_cb.clear()
        else:
            files = [f for f in os.listdir(self.preset_dir) if f.endswith('.epr')]
            self.presets_cb.addItems(files)

    def connect_command(self):
        self.rename_bt.clicked.connect(self.run_rename)
        self.check_rename_bt.clicked.connect(self.check_rename)
        self.export_split_bt.clicked.connect(self.run_export_split_mov)

    def check_rename(self):
        selected_clip = self.get_selected_clip()
        if not selected_clip:
            return
        names_list = self.get_name_list(total_num=len(selected_clip))
        for name in names_list:
            self.info_broad.add_line(f'{name}')
        self.info_broad.add_line(f'一共有{len(selected_clip)}个clip被选中')
        self.info_broad.add_line(f'[pass]检查命名完成')

    def run_rename(self):
        selected_clip = self.get_selected_clip()
        if not selected_clip:
            return
        names_list = self.get_name_list(total_num=len(selected_clip))

        for clip, name in zip(selected_clip, names_list):
            clip.name = name
        self.info_broad.add_line(f'[pass]重命名完成')

    def run_export_split_mov(self):
        selected_clip = self.get_selected_clip()
        if not selected_clip:
            return

        output_folder = self.export_dir_input.text()
        if not output_folder or not os.path.isdir(output_folder):
            self.info_broad.add_line(f'[error]输出目录不存在 {output_folder}')
            return

        preset_file = os.path.join(self.preset_dir, self.presets_cb.currentText())

        if not preset_file or not os.path.exists(preset_file):
            self.info_broad.add_line(f'[error]预设文件不存在 {preset_file}')
            return

        project = pymiere.objects.app.project
        active_sequence = project.activeSequence

        # 保存原始入点和出点
        original_in = active_sequence.getInPoint()
        original_out = active_sequence.getOutPoint()

        ext = self.output_ext_cb.currentText()

        for clip in selected_clip:
            output_file = os.path.join(output_folder, f'{clip.name}.{ext}')
            print(clip, clip.start, clip.end)

            # 设置入点和出点
            active_sequence.setInPoint(clip.start)
            active_sequence.setOutPoint(clip.end)
            result = active_sequence.exportAsMediaDirect(output_file, preset_file, 1)
            if result == 'No Error':
                self.info_broad.add_line(f'导出完成 {output_file}')
            else:
                self.info_broad.add_line(f'[error]导出失败 {result}')

        self.info_broad.add_line(f'[pass]所有视频导出完成')

        # 恢复原始入点和出点
        active_sequence.setInPoint(original_in)
        active_sequence.setOutPoint(original_out)

    def get_name_list(self, total_num):
        start_name = self.rename_start_input.text()
        interval_num = self.interval_num_box.value()
        try:
            start_num = int(start_name)
        except ValueError:
            return []
        name_list = []
        for i in range(total_num):
            num = start_num + i * interval_num
            name = f"{num:0{len(start_name)}d}"
            name_list.append(name)
        return name_list

    def get_selected_clip(self):
        try:
            project = pymiere.objects.app.project
            active_sequence = project.activeSequence
            selected = active_sequence.getSelection()
            selected = [selected[i] for i in range(selected.length) if selected[i].mediaType == 'Video']
        except Exception as e:
            self.info_broad.add_line(f'[error]获取选中片段失败: {traceback.format_exc()}')
            logger.error(traceback.format_exc())
            return []

        return selected
