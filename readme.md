### 关于PMTM
PMTM（PM Time Machine）是为vfx行业制片使用的一些小工具集，旨在提升工作效率，免去一些繁杂重复的事务和操作。

> 每次点击按钮，就像时间机器一样“快进”到任务完成。

![](https://lingyunfx-1259219315.cos.ap-beijing.myqcloud.com/pic/20250610232418.png)


### 现有功能概述
- 扫描Maya文件中的reference，并替换
- 扫描Maya文件的时间范围
- 扫描视频信息（比如帧数，分辨率，色彩空间，编码等）
- 序列帧/视频互转
- 图片拼图
- 图片添加反馈文字

### 环境部署
这里使用miniconda做环境管理，python使用3.10
```shell
# 创建conda环境
conda create -n pmtm python=3.10 -y

# 激活conda环境
conda activate pmtm

# 安装所需库
pip install -r requirements.txt
```

### 第三方库修改
为了在表格中显示图片，这里有在 `dayu_widgets.utils.line` 后添加
```python
# line 340
@icon_formatter.register(QtGui.QPixmap)
def _(input_object):
    return input_object
```

为了打包后找到资源文件，修改了 `dayu_widgets.__init__` 中的静态文件目录
```python
# line 12
DEFAULT_STATIC_FOLDER = './resource'
```

为实现扫描文件时满足多个条件，修改了 `dayu_path.base.DayuPath.scan` 函数
```python
# line 493
avaliable_files = all_files
if regex_pattern:
    avaliable_files = (f for f in avaliable_files if (compiled_regex.match(f)))
if ext_filters:
    avaliable_files = (f for f in avaliable_files if f.lower().endswith(ext_filters))
if function_filter:
    avaliable_files = (f for f in avaliable_files if function_filter(f))
```

在Python 3.7+中，StopIteration 在 generator 内部抛出时行为改变（参见 PEP 479）  
修改 `dayu_path.base.DayuPath.scan`
```python
# line 553
# before
if not recursive:
    raise StopIteration

# after
if not recursive:
    return
```

### 打包
```shell
pyinstaller main.py -i app.ico --hidden-import=PySide2 --hidden-import=PySide2.QtSvg --onefile -p .
```
