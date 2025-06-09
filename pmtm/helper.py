import os
from PySide2 import QtGui, QtCore


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


def get_image_path(name):
    return os.path.join('./resource', name)
