# GUI版本构建说明

## 安装依赖

```bash
# 安装GUI所需的依赖
pip install -r requirements-gui.txt
```

## 运行GUI版本

```bash
python gui_app.py
```

## 打包成EXE文件

### 方法1: 使用PyInstaller（推荐）

```bash
# 单文件模式（推荐，所有文件打包成一个exe）
pyinstaller --onefile --windowed --name="百度一刻相册下载器" gui_app.py

# 或使用配置文件
pyinstaller build.spec
```

生成的exe文件位于 `dist/` 目录下。

### 方法2: 使用spec文件（自定义配置）

```bash
# 使用提供的spec文件
pyinstaller build.spec
```

### PyInstaller 参数说明

- `--onefile`: 打包成单个exe文件
- `--windowed` / `-w`: 不显示控制台窗口（GUI程序）
- `--name`: 指定生成的exe文件名
- `--icon`: 指定应用图标（如果有的话）
- `--add-data`: 添加数据文件
- `--hidden-import`: 添加隐式导入的模块

### 常见问题

#### 1. 找不到模块

如果打包后运行提示找不到模块，在spec文件的 `hiddenimports` 中添加：

```python
hiddenimports=[
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'photographListDownload',
    'photographDownload',
    # 添加其他需要的模块
],
```

#### 2. 文件太大

- 使用 `--exclude-module` 排除不需要的模块
- 使用 UPX 压缩（默认已启用）
- 考虑使用目录模式而非单文件模式

#### 3. 杀毒软件误报

这是PyInstaller打包程序的常见问题，解决方法：
- 添加到杀毒软件白名单
- 数字签名exe文件
- 使用其他打包工具（如Nuitka）

## 目录结构

打包后的程序运行时会在exe所在目录创建以下文件/文件夹：

```
百度一刻相册下载器.exe
settings.json           # 配置文件
json/                   # 照片元数据
photograph/             # 下载的照片
download_history.json   # 下载历史
failed_downloads.json   # 失败记录
download.log           # 日志文件
```

## 发布

打包完成后，可以将 `dist/百度一刻相册下载器.exe` 分发给用户。

用户无需安装Python环境，双击exe即可运行。

## 功能特性

- ✅ 图形化界面，操作简单
- ✅ 配置保存与加载
- ✅ 实时日志显示
- ✅ 进度显示
- ✅ 日期过滤功能
- ✅ 打开下载目录
- ✅ 支持停止下载
- ✅ 多线程下载
- ✅ 断点续传
- ✅ 文件完整性校验

## 系统要求

- Windows 7 或更高版本
- 不需要安装Python（exe包含所有依赖）

## 界面预览

程序包含三个标签页：

1. **配置**: 填写BDSToken、Cookie等配置信息
2. **下载**: 执行下载操作，查看实时日志
3. **关于**: 查看使用说明和帮助信息
