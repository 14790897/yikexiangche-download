import json
import os
import re
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Optional

from PIL import Image

# ================= 配置区域 =================
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tiff"}
VIDEO_EXTENSIONS = {".mp4"}
TAG_DATETIME_ORIGINAL = 36867
MAX_WORKERS = 8  # 线程数
# ===========================================


def is_video_file(file_path: str) -> bool:
    return os.path.splitext(file_path)[1].lower() in VIDEO_EXTENSIONS


def get_exiftool_path():
    """
    在 Windows 上查找 exiftool.exe
    1. 先看系统 PATH 里有没有
    2. 再看脚本当前目录下有没有
    """
    # 检查全局命令
    if shutil.which("exiftool"):
        return "exiftool"

    # 脚本同目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_exe = os.path.join(script_dir, "exiftool.exe")
    if os.path.exists(local_exe):
        return local_exe

    return None


def fix_file_extension(file_path):
    """修正文件扩展名（如果格式不符）"""
    if is_video_file(file_path):
        return file_path
    try:
        with Image.open(file_path) as img:
            real_format = (img.format or "").lower()

        format_to_ext = {
            "jpeg": ".jpg",
            "png": ".png",
            "webp": ".webp",
            "tiff": ".tiff",
        }
        desired_ext = format_to_ext.get(real_format)
        if not desired_ext:
            return file_path

        current_ext = os.path.splitext(file_path)[1].lower()
        if current_ext in (".jpg", ".jpeg") and desired_ext == ".jpg":
            return file_path
        if current_ext == desired_ext:
            return file_path

        base_path = os.path.splitext(file_path)[0]
        new_path = f"{base_path}{desired_ext}"

        counter = 1
        while os.path.exists(new_path):
            new_path = f"{base_path}_fix{counter}{desired_ext}"
            counter += 1

        os.rename(file_path, new_path)
        return new_path
    except Exception:
        return file_path


def _normalize_exif_datetime(value: Any) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text[:19]
    if not re.match(r"^\d{4}:\d{2}:\d{2} \d{2}:\d{2}:\d{2}$", text):
        return None

    # 过滤 QuickTime/MP4 常见“未设置”的默认时间（以及明显不合理的年份）
    try:
        year = int(text[0:4])
        if year < 1970 or year > 2100:
            return None
        if year == 1904:
            return None
    except Exception:
        return None

    return text


def get_exif_date(file_path, exiftool_cmd):
    """PIL优先读取EXIF；读不到则用 ExifTool(JSON) 兜底。

    注意：视频（.mp4）不走 PIL，也不会因为读不到日期被当成“损坏”。

    Returns:
        (exif_date: str|None, is_corrupted: bool)
    """
    pil_failed = False
    is_video = is_video_file(file_path)

    if not is_video:
        try:
            with Image.open(file_path) as img:
                if hasattr(img, "getexif"):
                    exif = img.getexif()
                    if exif:
                        value = exif.get(TAG_DATETIME_ORIGINAL)
                        normalized = _normalize_exif_datetime(value)
                        if normalized:
                            return normalized, False
                getexif_legacy = getattr(img, "_getexif", None)
                if callable(getexif_legacy):
                    exif_data = getexif_legacy()
                    if isinstance(exif_data, dict) and exif_data:
                        value = exif_data.get(TAG_DATETIME_ORIGINAL)
                        normalized = _normalize_exif_datetime(value)
                        if normalized:
                            return normalized, False
        except Exception:
            pil_failed = True

    try:
        cmd = [
            exiftool_cmd,
            "-j",
            "-api",
            "QuickTimeUTC=1",
            "-api",
            "LargeFileSupport=1",
            "-d",
            "%Y:%m:%d %H:%M:%S",
            "-DateTimeOriginal",
            "-CreateDate",
            "-ModifyDate",
            "-MediaCreateDate",
            "-MediaModifyDate",
            "-TrackCreateDate",
            "-TrackModifyDate",
            "-EncodedDate",
            "-TaggedDate",
            "-ContentCreateDate",
            "-CreationDate",
            "-Keys:CreationDate",
            file_path,
        ]

        creationflags = 0
        if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            creationflags = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=creationflags,
        )
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            if isinstance(data, list) and data:
                meta = data[0] if isinstance(data[0], dict) else {}
                for key in (
                    "DateTimeOriginal",
                    "CreateDate",
                    "MediaCreateDate",
                    "TrackCreateDate",
                    "EncodedDate",
                    "TaggedDate",
                    "ContentCreateDate",
                    "CreationDate",
                    "Keys:CreationDate",
                    "ModifyDate",
                    "MediaModifyDate",
                    "TrackModifyDate",
                ):
                    normalized = _normalize_exif_datetime(meta.get(key))
                    if normalized:
                        return normalized, False

        if is_video:
            return None, False
        if pil_failed:
            return None, True
        return None, False
    except Exception:
        if is_video:
            return None, False
        if pil_failed:
            return None, True
        return None, False


def parse_date_from_filename(filename):
    """
    【核心逻辑】文件名时间分析 (优先级:微信 > 截图 > 时间戳 > 纯日期)
    返回 (类型, 时间字符串),失败返回 ("Unknown", None)
    """
    # 0. 最优先:微信图片 (mmexport1234567890123 或 wx_camera_1234567890123)
    wechat_match = re.search(r"(?:mmexport|wx_camera_)(\d{13})", filename)
    if wechat_match:
        try:
            timestamp = int(wechat_match.group(1)) / 1000.0
            if 631152000 < timestamp < 1893456000:  # 1990-2030
                return "WeChat", datetime.fromtimestamp(timestamp).strftime(
                    "%Y:%m:%d %H:%M:%S"
                )
        except Exception:
            pass
    
    # 1. 优先:截图/精确时间 (Screenshot_2019-10-02-11-51-30...)
    full_match = re.search(
        r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})[-_]?(\d{2})[-_]?(\d{2})[-_]?(\d{2})",
        filename,
    )
    if full_match:
        try:
            y, m, d, H, M, S = full_match.groups()
            return "Screenshot", f"{y}:{m}:{d} {H}:{M}:{S}"
        except Exception:
            pass

    # 2. 次选:Unix 时间戳 (严格13位毫秒或10位秒,以1开头)
    ts_matches = re.findall(r"(?<!\d)(1\d{9})(?!\d)|(1\d{12})(?!\d)", filename)
    for match in ts_matches:
        ts_str = match[0] or match[1]  # 10位或13位
        if not ts_str:
            continue
        try:
            timestamp = int(ts_str)
            if len(ts_str) == 13:
                timestamp /= 1000.0
            if 631152000 < timestamp < 1893456000:  # 1990-2030
                return "Timestamp", datetime.fromtimestamp(timestamp).strftime(
                    "%Y:%m:%d %H:%M:%S"
                )
        except Exception:
            continue

    # 3. 保底:纯日期 (20201120...) - 必须是合法日期
    date_match = re.search(r"(?<!\d)(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)", filename)
    if date_match:
        try:
            y, m, d = date_match.groups()
            return "DateOnly", f"{y}:{m}:{d} 12:00:00"
        except Exception:
            pass

    return "Unknown", None


def write_exif_date(exiftool_path, file_path, date_str):
    """调用 exiftool 写入时间 (调试版)"""
    try:
        cmd = [
            exiftool_path,
            "-overwrite_original",
            "-api",
            "QuickTimeUTC=1",
            "-api",
            "LargeFileSupport=1",
        ]

        if is_video_file(file_path):
            # MP4/QuickTime：写入媒体/轨道层的时间，必要时补 Encoded/Tagged。
            # 避免写 DateTimeOriginal（通常属于照片EXIF）以及文件系统时间（可能因权限失败）。
            cmd.extend(
                [
                    f"-CreateDate={date_str}",
                    f"-ModifyDate={date_str}",
                    f"-MediaCreateDate={date_str}",
                    f"-MediaModifyDate={date_str}",
                    f"-TrackCreateDate={date_str}",
                    f"-TrackModifyDate={date_str}",
                    f"-EncodedDate={date_str}",
                    f"-TaggedDate={date_str}",
                    f"-ContentCreateDate={date_str}",
                    f"-CreationDate={date_str}",
                ]
            )
        else:
            # 图片：保留原先的写入策略
            cmd.extend(
                [
                    # '-q', # 注释掉静默模式，我们要看报错
                    f"-DateTimeOriginal={date_str}",
                    f"-CreateDate={date_str}",
                    f"-ModifyDate={date_str}",
                    f"-MediaCreateDate={date_str}",
                    f"-MediaModifyDate={date_str}",
                    f"-TrackCreateDate={date_str}",
                    f"-TrackModifyDate={date_str}",
                    f"-FileCreateDate={date_str}",
                    f"-FileModifyDate={date_str}",
                ]
            )

        cmd.append(file_path)
        # 增加 text=True 以便直接读取文本报错
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        if result.returncode != 0:
            print(f"\n🚨 [ExifTool 报错] 文件: {os.path.basename(file_path)}")
            print(f"   错误信息: {result.stderr.strip()}")  # 打印出具体原因
            return False

        return True
    except Exception as e:
        print(f"\n🚨 [Python 报错] {e}")
        return False


def move_file(src_path, dest_folder):
    """移动并重命名防冲突"""
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder, exist_ok=True)

    filename = os.path.basename(src_path)
    dest_path = os.path.join(dest_folder, filename)

    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(dest_path):
        dest_path = os.path.join(dest_folder, f"{base}_{counter}{ext}")
        counter += 1

    shutil.move(src_path, dest_path)
    return dest_path


def process_single_file(args):
    """处理单个文件(多线程调用)"""
    file_path, file_name, exiftool_cmd, dirs = args
    result = {
        "file": file_name,
        "action": None,
        "type": None,
        "success": False
    }
    
    # 0. 修正文件扩展名（如果需要）
    file_path = fix_file_extension(file_path)
    file_name = os.path.basename(file_path)
    result["file"] = file_name
    
    # 1. 检查文件是否损坏
    exif_date, is_corrupted = get_exif_date(file_path, exiftool_cmd)
    if is_corrupted:
        move_file(file_path, dirs["corrupted"])
        result["action"] = "corrupted"
        result["success"] = True
        return result
    
    # 2. 检查 EXIF
    if exif_date:
        result["action"] = "skip"
        result["success"] = True
        return result
    
    # 3. 分析文件名
    f_type, date_str = parse_date_from_filename(file_name)
    
    if f_type != "Unknown" and date_str:
        # 4. 修复 EXIF 时间
        if write_exif_date(exiftool_cmd, file_path, date_str):
            result["type"] = f_type
            result["success"] = True
            
            if f_type == "WeChat":
                move_file(file_path, dirs["wechat"])
                result["action"] = "fixed_wechat"
            elif f_type == "Screenshot":
                move_file(file_path, dirs["screenshot"])
                result["action"] = "fixed_screenshot"
            else:
                move_file(file_path, dirs["date"])
                result["action"] = "fixed_date"
        else:
            result["action"] = "write_failed"
    else:
        # 5. 无法识别
        move_file(file_path, dirs["review"])
        result["action"] = "review"
        result["success"] = True
    
    return result


def process_directory(directory):
    exiftool_cmd = get_exiftool_path()
    if not exiftool_cmd:
        print("❌ 错误: 找不到 exiftool.exe")
        print("请下载 exiftool(-k).exe，重命名为 exiftool.exe")
        print("然后把它放在 C:\\Windows 目录下，或者和本脚本放在一起。")
        return

    print(f"🔧 使用 ExifTool: {exiftool_cmd}")
    print(f"🚀 正在扫描: {directory}")
    print(f"⚙️  使用 {MAX_WORKERS} 个线程并发处理\n")

    dirs = {
        "wechat": os.path.join(directory, "fixed_wechat"),
        "screenshot": os.path.join(directory, "fixed_screenshot"),
        "date": os.path.join(directory, "fixed_date"),
        "review": os.path.join(directory, "manual_review"),
        "corrupted": os.path.join(directory, "corrupted_files")
    }

    # 收集所有文件
    file_list = []
    for root, _, files in os.walk(directory):
        if any(x in root for x in ["fixed_wechat", "fixed_screenshot", "fixed_date", "manual_review", "corrupted_files"]):
            continue

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in VALID_EXTENSIONS or ext in VIDEO_EXTENSIONS:
                file_path = os.path.join(root, file)
                file_list.append((file_path, file, exiftool_cmd, dirs))
    
    if not file_list:
        print("❌ 未找到图片文件")
        return
    
    print(f"📂 找到 {len(file_list)} 个文件,开始处理...\n")

    stats = {"total": len(file_list), "fixed_wechat": 0, "fixed_screenshot": 0, "fixed_date": 0, "moved_review": 0, "corrupted": 0, "skipped": 0, "processed": 0}
    print_lock = threading.Lock()
    
    # 多线程处理
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_file, f): f for f in file_list}
        
        for future in as_completed(futures):
            result = future.result()
            
            with print_lock:
                stats["processed"] += 1
                progress = f"[{stats['processed']}/{stats['total']}]"
                
                if result["action"] == "corrupted":
                    print(f"{progress} ❌ {result['file']} - 损坏文件")
                    stats["corrupted"] += 1
                elif result["action"] == "skip":
                    print(f"{progress} ⏭️  {result['file']} - 已有EXIF")
                    stats["skipped"] += 1
                elif result["action"] == "fixed_wechat":
                    print(f"{progress} ✅ {result['file']} - 微信图片")
                    stats["fixed_wechat"] += 1
                elif result["action"] == "fixed_screenshot":
                    print(f"{progress} ✅ {result['file']} - 截图")
                    stats["fixed_screenshot"] += 1
                elif result["action"] == "fixed_date":
                    print(f"{progress} ✅ {result['file']} - {result['type']}")
                    stats["fixed_date"] += 1
                elif result["action"] == "review":
                    print(f"{progress} ⚠️  {result['file']} - 无法识别")
                    stats["moved_review"] += 1
                elif result["action"] == "write_failed":
                    print(f"{progress} ❌ {result['file']} - 写入失败")

    print("\n" + "=" * 40)
    print(" 🎉 完成！")
    print(f" 总文件数: {stats['total']}")
    print(f" 微信修复: {stats['fixed_wechat']}")
    print(f" 截图修复: {stats['fixed_screenshot']}")
    print(f" 日期修复: {stats['fixed_date']}")
    print(f" 人工审核: {stats['moved_review']}")
    print(f" 损坏文件: {stats['corrupted']}")
    print(f" 已有EXIF: {stats['skipped']}")
    print("=" * 40)
    input("按回车键退出...")  # 防止双击运行后窗口直接消失


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # 如果用户直接双击脚本，提示输入路径
        path = input("请输入图片文件夹路径 (可直接拖入文件夹): ").strip('"')
        if path:
            process_directory(path)
    else:
        process_directory(sys.argv[1])
