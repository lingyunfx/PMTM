import os
import re
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

        output_folder = self.export_dir_input.text().strip()
        if not output_folder or not os.path.isdir(output_folder):
            self.info_broad.add_line(f'[error]输出目录不存在 {output_folder}')
            return

        # Premiere 不接受混合分隔符的路径，统一成当前系统的分隔符。
        # Windows 上输入 D:/tmp/out 时，os.path.join 会拼成 D:/tmp/out\xxx.mp4 导致导出失败
        output_folder = os.path.normpath(output_folder)

        preset_file = os.path.normpath(os.path.join(self.preset_dir, self.presets_cb.currentText()))

        if not preset_file or not os.path.exists(preset_file):
            self.info_broad.add_line(f'[error]预设文件不存在 {preset_file}')
            return

        project = pymiere.objects.app.project
        active_sequence = project.activeSequence

        # 保存原始入点和出点
        original_in = active_sequence.getInPoint()
        original_out = active_sequence.getOutPoint()

        ext = self.output_ext_cb.currentText()

        # Premiere 内部按 88200Hz 的采样精度存序列入出点，传进去的秒数会被向下截断。
        # 落在非整数秒帧边界上的时间点会退到前一帧：入点退一帧，导出结果开头会多出
        # 上一个 clip 的最后一帧；出点退一帧（出点是 exclusive 的），末尾会少一帧。
        # 所以入出点都往后推半帧，量化后仍落在目标帧内，且不会跨到下一帧。
        try:
            fps = 1 / active_sequence.getSettings().videoFrameRate.seconds
            half_frame = 0.5 / fps
        except Exception:
            half_frame = 0
            logger.error(traceback.format_exc())

        for clip in selected_clip:
            output_file = os.path.join(output_folder, f'{clip.name}.{ext}')

            # 设置入点和出点
            active_sequence.setInPoint(clip.start.seconds + half_frame)
            active_sequence.setOutPoint(clip.end.seconds + half_frame)
            logger.info(f'导出 {clip.name} 入点={active_sequence.getInPoint()} '
                        f'出点={active_sequence.getOutPoint()}')
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
        start_name = self.rename_start_input.text().strip()
        interval_num = self.interval_num_box.value()

        # 取末尾连续的数字作为递增部分，前面的内容原样作为前缀，
        # 这样 0010、s0010、ep01_sh0010 这几种写法都能用
        match = re.match(r'^(.*?)(\d+)$', start_name)
        if not match:
            self.info_broad.add_line(f'[error]起始镜号需要以数字结尾，如 0010 或 s0010，当前为 {start_name}')
            return []

        prefix, digits = match.groups()
        start_num = int(digits)
        name_list = []
        for i in range(total_num):
            num = start_num + i * interval_num
            name = f'{prefix}{num:0{len(digits)}d}'
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
