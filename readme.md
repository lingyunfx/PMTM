为了在表格中显示图片，这里有在 dayu_widgets.utils.line:340 后添加
```python
@icon_formatter.register(QtGui.QPixmap)
def _(input_object):
    return input_object
```