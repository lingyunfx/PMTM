from dataclasses import dataclass
from typing import Callable

from pmtm.feature.scan_maya_ref import MayaRefScanUI
from pmtm.feature.scan_maya_frame import MayaFrameScanUI
from pmtm.feature.scan_movie_data import ScanMovieDataUI
from pmtm.feature.convert_tool import ConvertToolUI
from pmtm.feature.image_collage import ImageCollageUI
from pmtm.feature.add_text_to_image import AddTextToImageUI


@dataclass
class ToolData:

    name: str
    description: str
    group: str
    wiki_url: str
    icon: str
    widget: Callable
    enable: bool = True


DATA_LIST = [
    ToolData(name='Maya Reference扫描',
             group='',
             icon=r'./resource/scan_maya.png',
             wiki_url='https://lingyunfx.com/pmtm-doc/#1-%E6%89%AB%E6%8F%8F-Maya-Reference',
             widget=MayaRefScanUI,
             description="""
             扫描指定目录下的Maya文件（仅ma格式），获取其引用的reference路径。
             你可以对reference进行替换操作，也可以将扫描结果导出一个表格。
             (注意：替换操作会覆盖原始文件，替换前请备份) 
             """,
             ),

    ToolData(name='扫描Maya文件时间范围',
             group='',
             icon='./resource/frame_range.png',
             wiki_url='https://lingyunfx.com/pmtm-doc/#2-%E6%89%AB%E6%8F%8FMaya%E6%96%87%E4%BB%B6%E7%9A%84%E6%97%B6%E9%97%B4%E8%8C%83%E5%9B%B4',
             widget=MayaFrameScanUI,
             description="""
             扫描指定目录下的Maya文件（仅ma格式），获取其开始帧和结束帧，然后将结果导出一个表格。

             【使用方法】
             1.设置扫描路径，点击'扫描'按钮
             2.在中心视图查看扫描结果
             3.点击'导出表格'按钮
             """,
             ),

    ToolData(name='扫描视频信息',
             group='',
             icon='./resource/movie.png',
             wiki_url='https://lingyunfx.com/pmtm-doc/#3-%E6%89%AB%E6%8F%8F%E8%A7%86%E9%A2%91%E4%BF%A1%E6%81%AF',
             widget=ScanMovieDataUI,
             description="""
             扫描指定文件夹下的mov或mp4视频，也可以直接将文件拖拽到Table窗口中。
             工具会获取视频的'帧数','缩略图','帧数率'等信息，
             可将它导出为一个excel表格/或仅导出音频。
             """,
             ),
    ToolData(name='序列帧/视频互转',
             group='',
             icon='./resource/conversion.png',
             wiki_url='https://lingyunfx.com/pmtm-doc/#4-%E5%BA%8F%E5%88%97%E5%B8%A7-%E8%A7%86%E9%A2%91%E4%BA%92%E8%BD%AC',
             widget=ConvertToolUI,
             description="""
             可以将视频转换为序列帧，或者将序列帧转换为视频。

             【使用方法】
             1.首先进行文件扫描，选择要扫描的格式，点击'扫描'按钮
             2.在中心视图查看扫描结果
             3.设置输出的格式（帧率会对输出目标为视频的时候生效，而序列起始帧则对输出目标为序列的时候生效）
             4.点击'开始转换'按钮，等待任务完成。
             """,
             ),
    ToolData(name='图片拼图',
             group='',
             icon='./resource/image_collage.png',
             wiki_url='https://lingyunfx.com/pmtm-doc/#5-%E5%9B%BE%E7%89%87%E6%8B%BC%E5%9B%BE',
             widget=ImageCollageUI,
             enable=False,
             description="""
             可以将若干图片拼成一整张图片，比如将九张图片拼成一个九宫格。

             【使用方法】
             1.将图片拖拽到Table窗口中
             2.图片水平/垂直数量会自动计算，默认为正方形
             3.点击'输出'按钮，任务完成后，将自动打开图片。
             """,
             ),
    ToolData(name='图片添加反馈文字',
             group='',
             icon='./resource/add_text_to_image.png',
             wiki_url='https://lingyunfx.com/pmtm-doc/#6-%E5%9B%BE%E7%89%87%E6%B7%BB%E5%8A%A0%E5%8F%8D%E9%A6%88%E6%96%87%E5%AD%97',
             widget=AddTextToImageUI,
             description="""
             在图片上添加文字。
             输出时也可以进行选择是否拼成一整张图片。

             【使用方法】
             1.将图片拖拽到Table窗口中
             2.在表格中，选中条目后右键菜单，设置文字内容，颜色，大小
             3.输出选项中，选择"分别输出"或"拼接成一整张"。然后选择输出的文件格式。
             4.点击'开始任务'按钮，等待任务完成。
             （其它选项可以查看帮助文档详细说明）
             """,
             ),
]
