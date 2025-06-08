import os
import logging
from logging.handlers import TimedRotatingFileHandler

from PySide2 import QtCore
from pmtm import constant as const


def get_log_file_path():
    log_folder = os.path.join(os.path.expanduser('~'), '.pmtm', 'log')
    os.makedirs(log_folder, exist_ok=True)
    return os.path.join(log_folder, f'pmtm_tool.log')


def get_logger():
    """
    获取日志记录器
    """
    _logger = logging.getLogger()
    _logger.setLevel(logging.DEBUG)
    
    file_handler = TimedRotatingFileHandler(filename=get_log_file_path(),
                                            when='D',
                                            interval=1,
                                            encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'))
    file_handler.setLevel(logging.DEBUG)
    _logger.addHandler(file_handler)

    return _logger


class UserSetting(object):
    """
    用户设置
    """

    @staticmethod
    def get(key, default=None):
        setting = QtCore.QSettings(const.SETTING_FLAG)
        return setting.value(key, default)

    @staticmethod
    def set(key, value):
        setting = QtCore.QSettings(const.SETTING_FLAG)
        setting.setValue(key, value)


user_setting = UserSetting()
logger = get_logger()