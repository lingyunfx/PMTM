from dataclasses import dataclass
from typing import Callable

from pmtm.feature.scan_maya_ref import MayaRefScanUI
from pmtm.feature.scan_maya_frame import MayaFrameScanUI
from pmtm.feature.scan_movie_data import ScanMovieDataUI


@dataclass
class ToolData:

    name: str
    description: str
    group: str
    wiki_url: str
    icon: str
    widget: Callable


DATA_LIST = [
    ToolData(name='Maya Reference扫描',
             group='',
             icon=r'./resource/scan_maya.png',
             wiki_url='https://lingyunfx.com/maya-replace-ref-tool/',
             widget=MayaRefScanUI,
             description="""
             扫描目录下的ma文件，获取其所有reference路径。
              - 导出表格: 将ma文件与其引用了哪些reference导出一个表格
              - 替换: 为reference替换新的路径（注意:该操作会覆盖原始文件, 替换前请备份！）
             """,
             ),

    ToolData(name='扫描Maya文件时间范围',
             group='',
             icon='./resource/frame_range.png',
             wiki_url='',
             widget=MayaFrameScanUI,
             description="""
             该工具可以扫描ma文件，获取其开始帧和结束帧，然后将结果导出一个表格。
             """,
             ),

    ToolData(name='扫描mov视频信息',
             group='',
             icon='./resource/movie.png',
             wiki_url='',
             widget=ScanMovieDataUI,
             description="""
             扫描指定文件夹下的mov或mp4视频，也可以直接将文件拖拽到Table窗口中。
             工具会获取视频的'帧数','缩略图','帧数率'等信息，
             可将它导出为一个excel表格/或仅导出音频。
             """,
             )
]
