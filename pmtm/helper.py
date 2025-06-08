import os
import subprocess as sp

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


# 提取视频的音频
def extract_audio_from_mov(mov_file, output_audio_file):
    """
    提取视频的音频为wav
    """
    ffmpeg = user_setting.get('ffmpeg')
    cmd = f'"{ffmpeg}" -i "{mov_file}" -vn -acodec pcm_s16le -ar 44100 -ac 2 "{output_audio_file}"'
    print(cmd)
    sp.run(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)


def extract_thumbnail_from_mov(mov_file, output_image_file, frame=1):
    """
    输出视频指定帧数为缩略图
    """
    ffmpeg = user_setting.get('ffmpeg')
    cmd = f'"{ffmpeg}" -i "{mov_file}" -frames:v {frame} "{output_image_file}"'
    print(cmd)
    sp.run(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)


def get_frame_count(mov_file):
    """
    获取视频文件总帧数
    """
    ffprobe = user_setting.get('ffprobe')
    cmd = f'"{ffprobe}" -v error -select_streams v:0 -show_entries ' \
          f'stream=nb_frames -of default=noprint_wrappers=1:nokey=1 "{mov_file}"'
    print(cmd)
    process = sp.Popen(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    duration = process.stdout.readline().strip().decode()
    return int(duration)


def get_file_rate(file_path):
    """
    获取视频的帧数率
    """
    ffprobe = user_setting.get('ffprobe')
    cmd = f'"{ffprobe}" -v error -select_streams v:0 -show_entries stream=avg_frame_rate ' \
          f'-of default=noprint_wrappers=1:nokey=1 "{file_path}"'
    cmd = cmd.format(ffprobe, file_path)
    print(cmd)
    process = sp.Popen(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    rate = process.stdout.readline().strip().decode().split('/')[0]
    return rate


def get_file_colorspace(file_path):
    """
    获取视频的色彩空间
    """
    ffprobe = user_setting.get('ffprobe')
    cmd = '"{0}" -v error -select_streams v:0 -show_entries format_tags=uk.co.thefoundry.Colorspace ' \
          '-of default=noprint_wrappers=1:nokey=1 "{1}"'
    cmd = cmd.format(ffprobe, file_path)
    print(cmd)
    process = sp.Popen(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    colorspace = process.stdout.readline().strip().decode()
    return colorspace


def get_file_resolution(file_path):
    """
    获取视频的分辨率
    """
    ffprobe = user_setting.get('ffprobe')
    cmd = '"{0}" -v error -show_entries stream=width,height -of csv=p=0:s=x "{1}"'
    cmd = cmd.format(ffprobe, file_path)
    print(cmd)
    process = sp.Popen(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    resolution = process.stdout.readline().strip().decode()
    return resolution


def get_file_codex(file_path):
    """
    获取视频的编码
    """
    ffprobe = user_setting.get('ffprobe')
    cmd = '"{0}" -v error -select_streams v:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "{1}"'
    cmd = cmd.format(ffprobe, file_path)
    print(cmd)
    process = sp.Popen(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    codex = process.stdout.readline().strip().decode()
    return codex


def get_image_resolution(image_path):
    """
    获取图片的长宽
    """
    magick = user_setting.get('magick')
    cmd = f'"{magick}" identify -format "%wx%h" "{image_path}"'
    print(cmd)
    process = sp.Popen(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    size = process.stdout.readline().strip()
    w, h = str(size).split('x')
    return w, h


def scale_image(source_image, target_image, scale=1.0):
    """
    等比缩放图片
    """
    scale *= 100.0
    magick = user_setting.get('magick')
    cmd = f'{magick} identify {source_image} -resize {scale}% "{target_image}"'
    print(cmd)
    sp.run(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)


def get_image_path(name):
    return os.path.join('./resource', name)
