### 关于PMTM
PMTM（PM Time Machine）是为vfx行业制片使用的一些小工具集，旨在提升工作效率，免去一些繁杂重复的事务和操作。

> 每次点击按钮，就像时间机器一样“快进”到任务完成。

![](https://lingyunfx-1259219315.cos.ap-beijing.myqcloud.com/pic/20250608195016.png)


### 现有功能概述
- 扫描Maya文件中的reference，并替换
- 扫描Maya文件的时间范围
- 扫描视频信息（比如帧数，分辨率，色彩空间，编码等）
- 序列帧/视频互转

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
为了在表格中显示图片，这里有在 dayu_widgets.utils.line:340 后添加
```python
@icon_formatter.register(QtGui.QPixmap)
def _(input_object):
    return input_object
```