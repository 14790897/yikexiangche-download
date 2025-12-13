# 一刻相册一键下载

一刻相册一键全部下载工具，支持**命令行**和**图形界面**两种模式。

**特性**：多线程下载 + 断点续传 + 重复检测 + 失败重试 + 日志记录 + 日期过滤 + 完整性校验

---

## 📦 两种使用方式

### 🖥️ 方式1: GUI图形界面版（推荐新手）

直接双击运行，无需命令行操作！

#### 快速开始

```bash
# 1. 安装依赖
pip install -r requirements-gui.txt

# 2. 运行GUI
python gui_app.py

# 或直接双击
run_gui.bat
```

#### 打包成EXE

```bash
# 方法1: 双击运行打包脚本
build_exe.bat

# 方法2: 手动打包
pyinstaller --onefile --windowed --name="百度一刻相册下载器" gui_app.py
```

打包后的 `百度一刻相册下载器.exe` 无需Python环境即可运行！

#### GUI功能特性

- ✅ 可视化配置界面
- ✅ 实时日志显示
- ✅ 进度条显示
- ✅ 日期过滤设置
- ✅ 一键打开下载目录
- ✅ 配置保存/加载
- ✅ 三个标签页（配置/下载/关于）

---

### ⌨️ 方式2: 命令行版（适合高级用户）

#### 依赖

基于Python3的脚本，首先需要安装Python3

#### 安装第三方库

```bash
pip install requests
pip install tqdm
```

或一次性安装：
```bash
pip install -r requirements.txt
```

#### 准备配置

打开一刻相册网页端，按下F12，在DevTools内点击上方的`网络`，然后点击`Fetch/XHR`进行筛选。

![image](https://github.com/user-attachments/assets/ddbc2d08-ee89-4d47-b1a8-2363a7929e32)

点击列表的list?celienttype=70……，在请求标头找到`cookie`.三击全选复制。

![image](https://github.com/user-attachments/assets/f1f5b3d4-04dc-48a1-af52-e23f741d43bb)

点击上方负载，双击`bdstoken`的字段。

![image](https://github.com/user-attachments/assets/5fcfd587-91e4-4dfe-8380-efc12a55e6ce)

复制 `settings.json.example` 为 `settings.json`，然后填写对应的`bdstoken`和`Cookie`。

**注意**：如果`Cookie`值中有双引号，则用转义字符`\"`代替双引号`"`

#### 日期过滤（可选）

在 `settings.json` 中添加日期过滤配置：

```json
{
    "clienttype": 70,
    "bdstoken": "your_token",
    "need_thumbnail": 1,
    "need_filter_hidden": 0,
    "filter_date": "2025-01-01",
    "date_mode": "before",
    "Cookie": "your_cookie"
}
```

- `filter_date`: 过滤日期，格式 YYYY-MM-DD，留空表示不过滤
- `date_mode`: `before`=之前, `after`=之后

详见：[日期过滤使用说明.md](日期过滤使用说明.md)

#### 运行

```bash
# 1. 先获取照片元数据
python photographListDownload.py

# 2. 然后下载照片
python photographDownload.py
```

等待完成即可！

---

## 📁 目录结构

```
.
├── gui_app.py                    # GUI程序
├── photographListDownload.py      # 元数据下载脚本
├── photographDownload.py          # 照片下载脚本
├── settings.json                  # 配置文件（需自行创建）
├── settings.json.example          # 配置文件模板
├── requirements.txt               # 命令行版依赖
├── requirements-gui.txt           # GUI版依赖
├── build.spec                     # PyInstaller配置
├── run_gui.bat                    # GUI启动脚本
├── build_exe.bat                  # 打包脚本
├── json/                          # 照片元数据目录
├── photograph/                    # 下载的照片目录
├── download_history.json          # 下载历史记录
└── failed_downloads.json          # 失败下载记录
```

---

## 🔧 高级功能

### 断点续传

程序会自动记录下载进度，中断后重新运行会继续下载未完成的文件。

### 完整性校验

每个文件下载后会计算MD5哈希值，重新运行时会校验文件完整性。

### 失败重试

下载失败的文件会被记录，重新运行时会优先下载这些文件，最多重试5次。

### 并发下载

默认使用32个线程并发下载，可在代码中修改 `max_workers` 参数。

---

## 📝 注意事项

- ⚠️ 你复制的数据包含隐私信息，请勿告诉他人
- ⚠️ Cookie有时效性，失效后需要重新获取
- ⚠️ `settings.json` 已加入 `.gitignore`，不会被提交到Git
- ⚠️ 建议定期备份 `download_history.json`

---

## 🐛 常见问题

### 1. 提示认证失败

Cookie或bdstoken失效，需要重新从浏览器获取。

### 2. 下载速度慢

可以调整并发数（`max_workers`）或检查网络连接。

### 3. 文件大小限制

默认限制500MB，可在代码中修改 `max_file_size` 参数。

### 4. GUI打包后无法运行

确保使用 `--hidden-import` 添加了所有依赖模块，或使用提供的 `build.spec` 文件。

---

## 📄 相关文档

- [配置说明.md](配置说明.md) - 详细的配置说明
- [日期过滤使用说明.md](日期过滤使用说明.md) - 日期过滤功能说明
- [BUILD.md](BUILD.md) - GUI打包详细说明

---

## 📜 License

MIT License

---

## 🙏 致谢

感谢所有贡献者和使用者！

如有问题欢迎提Issue。
