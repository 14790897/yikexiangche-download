# fix_exif.py 使用说明

## 功能简介

`fix_exif.py` 用于批量修复图片/视频的拍摄时间（EXIF/媒体时间）。当文件本身缺少时间信息时，脚本会尝试从文件名中解析日期并写回，同时对无法识别或损坏的文件进行分类移动，便于后续整理。

## 支持格式

- 图片: `.jpg` `.jpeg` `.png` `.webp` `.heic` `.tiff`
- 视频: `.mp4`

## 依赖

1. Python 3
2. ExifTool（必需）
   - 推荐将 `exiftool.exe` 放在以下任一位置：
     - 与 `fix_exif.py` 同目录
     - `C:\Windows` 或已加入 `PATH`
3. Pillow（Python 包）：`pip install pillow`

## 使用方法

### 命令行运行

```bash
python fix_exif.py "D:\your\photo\folder"
```

## 处理逻辑（简要）

1. **修正扩展名**：如果图片扩展名与实际格式不一致，会自动更正。
2. **读取时间**：
   - 优先用 PIL 读取图片 EXIF。
   - 失败时用 ExifTool 读取（图片/视频都适用）。
3. **已有时间**：如果已存在有效时间信息，则跳过。
4. **从文件名解析时间**（优先级）：
   - 微信图片：`mmexport1234567890123` / `wx_camera_1234567890123`
   - 截图类：`Screenshot_2019-10-02-11-51-30`
   - 时间戳：10 位或 13 位 Unix 时间戳
   - 纯日期：`20201120` 这类连续日期
5. **写入时间并移动文件**：
   - 成功修复会移动到分类目录。
   - 无法识别或损坏会移动到指定目录。

## 输出目录

脚本会在目标目录下自动创建并移动文件：

- `fixed_wechat`：从微信时间戳修复
- `fixed_screenshot`：从截图时间修复
- `fixed_date`：从其他日期/时间戳修复
- `manual_review`：无法识别时间
- `corrupted_files`：疑似损坏

## 注意事项

- 脚本会移动文件，请先备份重要数据。
- `.mp4` 仅写入媒体层时间，不写图片 EXIF 字段。视频处理并不完善
- 若提示找不到 ExifTool，请确认 `exiftool.exe` 可执行且在 PATH 或脚本目录。
