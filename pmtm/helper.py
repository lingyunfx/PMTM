import os
import subprocess as sp
from glob import glob

from PySide2 import QtGui, QtCore
from pmtm.core import user_setting


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


def scan_files(scan_folder, is_include, ext_list):
    """
    扫描文件, is_include 为 True 时, 包含子目录, ext_list 为文件扩展名列表
    ext_list 示例: ['.ma', '.mb']
    """
    if not os.path.isdir(scan_folder):
        return []
    
    file_list = []
    for root, dirs, files in os.walk(scan_folder):
        for file in files:
            if file.startswith('.'):
                continue
            if any(file.endswith(ext) for ext in ext_list):
                file_list.append(os.path.join(root, file))
        if not is_include:
            break
    return file_list


def get_resource_file(name):
    return os.path.join('./resource', name)


def list_resource_files(ext):
    return glob('./resource/*' + ext)


def check_depend_tool_exist():
    """
    检查依赖软件
    """
    ffmpeg = user_setting.get('ffmpeg')
    ffprobe = user_setting.get('ffprobe')
    magick = user_setting.get('magick')

    for tool in (ffmpeg, ffprobe, magick):
        if not tool or not tool.endswith('.exe'):
            return False
    return True


def open_folder(path):
    """
    从资源管理器打开文件夹
    """
    sp.Popen(['explorer.exe', path])


def open_file(path):
    """
    调用默认程序打开文件
    """
    os.startfile(path)
