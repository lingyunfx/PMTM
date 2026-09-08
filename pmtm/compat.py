"""
第三方库的运行时补丁

原本这些修改需要手工去改 site-packages 里的源码，换成 uv 管理后不要再这么做：
uv 默认用硬链接从全局缓存装包，改 .venv 里的文件等于改全局缓存，会影响本机
所有用到该版本的项目。所以统一改成在导入时打补丁，不碰 .venv。

注意：_patch_dayu_path_scan 里的 scan 是照着 dayu-path 0.5.2 的实现改的，
升级 dayu-path 时需要重新和上游比对一次。
"""
import os
import re
import bisect

from PySide2 import QtGui


def _patch_icon_formatter():
    """
    让 dayu_widgets 的表格支持直接显示 QPixmap（用于缩略图列）
    """
    from dayu_widgets.utils import icon_formatter

    @icon_formatter.register(QtGui.QPixmap)
    def _(input_object):
        return input_object


def _patch_dayu_path_scan():
    """
    修正 dayu_path.DayuPath.scan 的两个问题：
    1. 原实现里各个过滤条件都基于 all_files，导致多个条件无法叠加生效
    2. 在生成器内部 raise StopIteration，Python 3.7+ 会报 RuntimeError（PEP 479）
    """
    from dayu_path.base import DayuPath, SCAN_IGNORE

    def scan(self, recursive=False, regex_pattern=None, ext_filters=None,
             function_filter=None, ignore_invisible=True):
        scan_path, file_flag = (self, False) if self.isdir() else (self.parent, True)
        compiled_regex = re.compile(regex_pattern) if regex_pattern else None
        for root, sub_folders, sub_files in os.walk(scan_path):
            seq_list = {}
            if ignore_invisible:
                all_files = (DayuPath(root).child(f) for f in sub_files
                             if not f.startswith(SCAN_IGNORE['start']))
            else:
                all_files = (DayuPath(root).child(f) for f in sub_files)

            # 逐层叠加过滤条件，保证多个条件同时生效
            avaliable_files = all_files
            if regex_pattern:
                avaliable_files = (f for f in avaliable_files if compiled_regex.match(f))
            if ext_filters:
                avaliable_files = (f for f in avaliable_files if f.lower().endswith(ext_filters))
            if function_filter:
                avaliable_files = (f for f in avaliable_files if function_filter(f))

            for single_file in avaliable_files:
                pattern_path = single_file.absolute().to_pattern()
                frames_list = seq_list.setdefault(pattern_path, [])
                if single_file != pattern_path:
                    bisect.insort(frames_list, single_file.frame)

            if file_flag:
                k = self.absolute().to_pattern()
                v = seq_list.get(k, None)
                if v is not None:
                    k.frames = v
                    k.missing = (sorted(set(range(v[0], v[-1] + 1)) - set(v))) if v else []
                    yield k
                return

            if seq_list:
                for k, v in seq_list.items():
                    k.frames = v
                    k.missing = (sorted(set(range(v[0], v[-1] + 1)) - set(v))) if v else []
                    yield k

            if not recursive:
                return

    DayuPath.scan = scan


def apply_patches():
    _patch_icon_formatter()
    _patch_dayu_path_scan()
