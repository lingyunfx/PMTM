import subprocess as sp
from pmtm.core import user_setting, logger
from pmtm.helper import get_resource_file


# -----------------------图像处理--------------------------------
def get_image_resolution(image_path):
    """
    获取图片的长宽
    """
    magick = user_setting.get('magick')
    cmd = f'"{magick}" identify -format "%wx%h" "{image_path}"'
    logger.debug(f'执行命令: {cmd}')
    process = sp.Popen(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    size = process.stdout.readline().strip().decode()
    w, h = str(size).split('x')
    return w, h


def scale_image(source_image, target_image, scale=1.0):
    """
    等比缩放图片
    """
    scale *= 100.0
    magick = user_setting.get('magick')
    cmd = f'{magick} identify {source_image} -resize {scale}% "{target_image}"'
    logger.debug(f'执行命令: {cmd}')
    sp.run(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)


def extract_thumbnail_from_image(image_file, output_image_file):
    """
    输出图片为缩略图
    """
    magick = user_setting.get('magick')
    cmd = f'"{magick}" convert "{image_file}" -thumbnail 192x108 "{output_image_file}"'
    logger.debug(f'执行命令: {cmd}')
    sp.run(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)


def run_collage_images(image_files, output_image_file, horizontal_count, vertical_count):
    """
    将图片拼接为一张图片
    """
    magick = user_setting.get('magick')
    cmd = f'"{magick}" montage {" ".join(image_files)} -tile {horizontal_count}x{vertical_count} -geometry +0+0 -background black "{output_image_file}"'
    logger.debug(f'执行命令: {cmd}')
    sp.run(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)


def run_add_text_to_image(image_file, output_image_file, text, color, size):
    """
    为图片添加文字，文字在图片底部中心位置
    """
    magick = user_setting.get('magick')
    font_file = get_resource_file('msyh.ttf')
    cmd = f'"{magick}" convert "{image_file}" -font {font_file} -gravity South -pointsize {size} -fill "{color}" -annotate +0+10 "{text}" -font "{font_file}" "{output_image_file}"'
    logger.debug(f'执行命令: {cmd}')
    sp.run(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)


# -----------------------视频处理--------------------------------
def extract_audio_from_mov(mov_file, output_audio_file):
    """
    提取视频的音频为wav
    """
    ffmpeg = user_setting.get('ffmpeg')
    cmd = f'"{ffmpeg}" -i "{mov_file}" -vn -acodec pcm_s16le -ar 44100 -ac 2 "{output_audio_file}"'
    logger.debug(f'执行命令: {cmd}')
    sp.run(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)


def extract_thumbnail_from_mov(mov_file, output_image_file, frame=1):
    """
    输出视频指定帧数为缩略图
    """
    ffmpeg = user_setting.get('ffmpeg')
    cmd = f'"{ffmpeg}" -i "{mov_file}" -frames:v {frame} "{output_image_file}"'
    logger.debug(f'执行命令: {cmd}')
    sp.run(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)


def get_video_frame_count(mov_file):
    """
    获取视频文件总帧数
    """
    ffprobe = user_setting.get('ffprobe')
    cmd = f'"{ffprobe}" -v error -select_streams v:0 -show_entries ' \
          f'stream=nb_frames -of default=noprint_wrappers=1:nokey=1 "{mov_file}"'
    logger.debug(f'执行命令: {cmd}')
    process = sp.Popen(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    duration = process.stdout.readline().strip().decode()
    return int(duration)


def get_video_rate(file_path):
    """
    获取视频的帧数率
    """
    ffprobe = user_setting.get('ffprobe')
    cmd = f'"{ffprobe}" -v error -select_streams v:0 -show_entries stream=avg_frame_rate ' \
          f'-of default=noprint_wrappers=1:nokey=1 "{file_path}"'
    cmd = cmd.format(ffprobe, file_path)
    logger.debug(f'执行命令: {cmd}')
    process = sp.Popen(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    rate = process.stdout.readline().strip().decode().split('/')[0]
    return rate


def get_video_colorspace(file_path):
    """
    获取视频的色彩空间
    """
    ffprobe = user_setting.get('ffprobe')
    cmd = '"{0}" -v error -select_streams v:0 -show_entries format_tags=uk.co.thefoundry.Colorspace ' \
          '-of default=noprint_wrappers=1:nokey=1 "{1}"'
    cmd = cmd.format(ffprobe, file_path)
    logger.debug(f'执行命令: {cmd}')
    process = sp.Popen(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    colorspace = process.stdout.readline().strip().decode()
    return colorspace


def get_video_resolution(file_path):
    """
    获取视频的分辨率
    """
    ffprobe = user_setting.get('ffprobe')
    cmd = '"{0}" -v error -show_entries stream=width,height -of csv=p=0:s=x "{1}"'
    cmd = cmd.format(ffprobe, file_path)
    logger.debug(f'执行命令: {cmd}')
    process = sp.Popen(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    resolution = process.stdout.readline().strip().decode()
    return resolution


def get_video_codex(file_path):
    """
    获取视频的编码
    """
    ffprobe = user_setting.get('ffprobe')
    cmd = '"{0}" -v error -select_streams v:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "{1}"'
    cmd = cmd.format(ffprobe, file_path)
    logger.debug(f'执行命令: {cmd}')
    process = sp.Popen(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    codex = process.stdout.readline().strip().decode()
    return codex


# -----------------------格式转换--------------------------------
def convert_seq_to_video(seq_file, output_video_file, start_frame=1, fps=25):
    """
    将图片序列转换为视频
    args_example:
        seq_file: D:\show\TST\0001.%04d.png
        output_video_file: D:\show\TST\0001.mp4
        start_frame: 1
        fps: 25
    """
    ffmpeg = user_setting.get('ffmpeg')
    cmd = f'"{ffmpeg}" -y -start_number {start_frame} -r {fps} -i "{seq_file}" -vcodec h264 "{output_video_file}"'
    logger.debug(f'执行命令: {cmd}')
    sp.run(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)


def convert_video_to_seq(video_file, output_seq_file, start_frame=1):
    """
    将视频转换为图片序列
    args_example:
        video_file: D:\show\TST\0001.mp4
        output_seq_file: D:\show\TST\0001.%04d.png
        start_frame: 1
    """
    ffmpeg = user_setting.get('ffmpeg')
    cmd = f'"{ffmpeg}" -i "{video_file}" -start_number {start_frame} "{output_seq_file}"'
    logger.debug(f'执行命令: {cmd}')
    sp.run(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)


def convert_seq_to_seq(source_seq_file, output_seq_file, source_start_frame=1, output_start_frame=1):
    """
    将序列帧转换为序列帧
    args_example:
        source_seq_file: D:\show\TST\0001.%04d.png
        output_seq_file: D:\show\TST\0001.%04d.png
        source_start_frame: 1
        output_start_frame: 1
    """
    ffmpeg = user_setting.get('ffmpeg')
    cmd = f'"{ffmpeg}" -start_number {source_start_frame} -i "{source_seq_file}" -qscale:v 2 -start_number {output_start_frame} "{output_seq_file}"'
    logger.debug(f'执行命令: {cmd}')
    sp.run(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)


def convert_video_to_video(source_video_file, output_video_file):
    """
    将视频转换为视频
    args_example:
        source_video_file: D:\show\TST\0001.mp4
        output_video_file: D:\show\TST\0001.mp4
    """
    ffmpeg = user_setting.get('ffmpeg')
    cmd = f'"{ffmpeg}" -i "{source_video_file}" -qscale:v 2 "{output_video_file}"'
    logger.debug(f'执行命令: {cmd}')
    sp.run(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
