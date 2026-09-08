### 关于PMTM
PMTM（PM TimeMachine）是为视效行业制片准备的一些小工具集，旨在提升工作效率，免去一些繁杂重复的事务和操作。

> 每次点击按钮，就像时间机器一样“快进”到任务完成。

![](https://lingyunfx-1259219315.cos.ap-beijing.myqcloud.com/pic/20250612184139.png)


### 现有功能概述
- 扫描Maya文件中的reference，并替换
- 扫描Maya文件的时间范围
- 扫描视频信息（比如帧数，分辨率，色彩空间，编码等）
- 序列帧/视频互转
- 图片添加反馈文字
- PR辅助工具（分别导出clip，批量命名clip）

### 环境部署
项目使用 [uv](https://docs.astral.sh/uv/) 管理依赖和虚拟环境，Python 版本为 3.10。

如果还没有 uv，先安装（Windows PowerShell）：
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS / Linux：
```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

然后在项目根目录同步环境，uv 会自动下载 Python 3.10、创建 `.venv` 并按 `uv.lock` 安装所有依赖：
```shell
uv sync
```

### 启动
```shell
uv run pmtm
```
`uv run` 会在执行前自动检查并同步环境，所以日常开发直接跑这一条命令即可，不需要手动激活虚拟环境。


### 第三方库的补丁
dayu_widgets 和 dayu_path 有几处问题需要修正。
修改统一放在 `pmtm/compat.py` 里做运行时补丁，由 `pmtm.run()` 在启动时
自动应用，`.venv` 保持干净，环境随时可以重建。

具体包含：

- 为 `dayu_widgets.utils.icon_formatter` 注册 `QPixmap` 分支，使表格中可以直接显示图片缩略图
- 修正 `dayu_path.base.DayuPath.scan`，让 `regex_pattern` / `ext_filters` / `function_filter`
  多个过滤条件可以叠加生效（原实现每个条件都基于未过滤的 `all_files`）
- 修正 `DayuPath.scan` 在生成器内部 `raise StopIteration` 的写法，改为 `return`
  （Python 3.7+ 中该写法会触发 RuntimeError，参见 PEP 479）

其中 `scan` 是整体替换的，代码照着 dayu-path 0.5.2 的实现改，升级 dayu-path 时
需要重新和上游比对一次。

### 资源路径
代码中的资源引用都是 `./resource/xxx` 这种相对路径，`pmtm.run()` 启动时会先切换到项目根目录
（打包后则是 PyInstaller 解压资源的临时目录），所以在任意路径下执行 `uv run pmtm` 都能正常找到资源文件。

### 版本号
版本号只在 `pmtm/constant.py` 的 `VERSION` 里维护，`pyproject.toml` 通过 hatchling 动态读取，
发版时改一处就够了。

### 打包
```shell
uv sync --all-groups
uv run pyinstaller main.py -n PMTM -i app.ico --onefile -p . --add-data "resource;resource" --collect-data dayu_widgets --hidden-import=PySide2 --hidden-import=PySide2.QtSvg --noconfirm
```
产物是 `dist/PMTM.exe`。项目里的 `resource` 目录和 dayu_widgets 自带的静态文件都已经打进 exe，
分发时单个文件就够，不用再往 exe 旁边拷贝资源目录。

注意打包只是把 `resource` 复制了一份进 exe，项目里的这个目录不能删：
源码中有二十多处直接引用 `./resource/xxx`，删掉之后开发时跑不起来，打包也会失败。

注意 `--add-data` 的路径分隔符在 Windows 上是 `;`，macOS/Linux 上是 `:`。
