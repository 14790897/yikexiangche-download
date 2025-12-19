import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

from PIL import Image

# ================= 配置 =================
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tiff"}
TAG_DATETIME_ORIGINAL = 36867
# =======================================


def get_exiftool_path():
    if shutil.which("exiftool"):
        return "exiftool"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local = os.path.join(script_dir, "exiftool.exe")
    return local if os.path.exists(local) else None


def get_exif_date_str(file_path):
    """获取 EXIF 时间字符串 (YYYY:MM:DD HH:MM:SS)"""
    try:
        img = Image.open(file_path)
        exif = img._getexif()
        return exif.get(TAG_DATETIME_ORIGINAL) if exif else None
    except:
        return None


def str_to_dt(date_str):
    """将字符串转换为 datetime 对象以便比较"""
    try:
        # 支持两种格式: "2020:11:20 19:28:27" 或 "2020-11-20 19:28:27"
        date_str = date_str.replace("-", ":").replace("/", ":")
        return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
    except:
        return None


def parse_date_enhanced(filename):
    """
    【核心逻辑】文件名时间分析 (优先级：截图 > 时间戳 > 纯日期)
    """
    # 1. 优先：截图/精确时间 (Screenshot_2019-10-02-11-51-30...)
    full_match = re.search(
        r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})[-_]?(\d{2})[-_]?(\d{2})[-_]?(\d{2})",
        filename,
    )
    if full_match:
        try:
            y, m, d, H, M, S = full_match.groups()
            return f"{y}:{m}:{d} {H}:{M}:{S}"
        except:
            pass

    # 2. 次选：Unix 时间戳 (13位/10位，以1开头)
    ts_matches = re.findall(r"(1\d{9,12})", filename)
    for ts_str in ts_matches:
        try:
            timestamp = int(ts_str)
            if len(ts_str) == 13:
                timestamp /= 1000.0
            if 631152000 < timestamp < 1893456000:  # 1990-2030
                return datetime.fromtimestamp(timestamp).strftime("%Y:%m:%d %H:%M:%S")
        except:
            continue

    # 3. 保底：纯日期 (20201120...)
    date_match = re.search(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})", filename)
    if date_match:
        try:
            y, m, d = date_match.groups()
            if 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
                return f"{y}:{m}:{d} 12:00:00"
        except:
            pass

    return None


def write_exif(exiftool, path, date_str):
    try:
        flags = 0x08000000 if os.name == "nt" else 0
        cmd = [
            exiftool,
            "-overwrite_original",
            "-q",
            f"-DateTimeOriginal={date_str}",
            f"-CreateDate={date_str}",  # 2. 补充标签 (增加兼容性)
            f"-ModifyDate={date_str}",
            f"-MediaCreateDate={date_str}",
            # 3. 【关键】修改文件系统的“创建时间”和“修改时间”
            # 这是 Windows 资源管理器最喜欢看的东西，尤其是对于 PNG
            f"-FileCreateDate={date_str}",
            f"-FileModifyDate={date_str}",
            path,
        ]
        res = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags
        )
        return res.returncode == 0
    except:
        return False


def main():
    if len(sys.argv) < 2:
        print("❌ 用法: python post_process_check.py <目录路径>")
        return

    target_dir = sys.argv[1]
    exiftool = get_exiftool_path()
    if not exiftool:
        print("❌ 找不到 exiftool.exe")
        return

    # 准备文件夹
    dir_new = os.path.join(target_dir, "fixed_new")  # 之前没 EXIF，现在补上的
    dir_corrected = os.path.join(
        target_dir, "fixed_corrected"
    )  # 之前有错 EXIF，现在改对的
    dir_verified = os.path.join(target_dir, "verified_ok")  # 之前就有 EXIF 且是对的

    for d in [dir_new, dir_corrected, dir_verified]:
        if not os.path.exists(d):
            os.makedirs(d)

    print(f"🕵️  开始深度检查: {target_dir}")
    print("------------------------------------------------")

    stats = {"new": 0, "corrected": 0, "verified": 0, "unknown": 0}

    for filename in os.listdir(target_dir):
        file_path = os.path.join(target_dir, filename)

        # 跳过文件夹和非图片
        if not os.path.isfile(file_path):
            continue
        if os.path.splitext(filename)[1].lower() not in VALID_EXTENSIONS:
            continue

        # 1. 尝试从文件名获取“真理时间”
        file_date_str = parse_date_enhanced(filename)

        # 2. 获取图片现有的 EXIF 时间
        current_exif_str = get_exif_date_str(file_path)

        if not file_date_str:
            # 文件名里啥都没有，没法判断对错，只能跳过
            # print(f"⚠️  无法识别文件名时间: {filename}")
            stats["unknown"] += 1
            continue

        # 3. 核心判断逻辑
        should_write = False
        reason = ""
        target_folder = ""

        if not current_exif_str:
            # 情况 A: 根本没 EXIF
            should_write = True
            reason = "无EXIF -> 补全"
            target_folder = dir_new
            stats_key = "new"
        else:
            # 情况 B: 有 EXIF，需要比对
            dt_file = str_to_dt(file_date_str)
            dt_exif = str_to_dt(current_exif_str)

            if dt_file and dt_exif:
                # 计算时间差（秒）
                diff = abs((dt_file - dt_exif).total_seconds())

                if diff > 120:  # 允许 2 分钟的误差
                    should_write = True
                    reason = f"时间不符(EXIF:{current_exif_str} vs 文件名:{file_date_str}) -> 纠错"
                    target_folder = dir_corrected
                    stats_key = "corrected"
                else:
                    # 时间基本一致，不需要修改，直接移动到 verified
                    try:
                        shutil.move(file_path, os.path.join(dir_verified, filename))
                        print(f"✅ [验证通过] {filename}")
                        stats["verified"] += 1
                    except:
                        pass
                    continue
            else:
                # 日期格式解析不了，保守起见不覆盖，除非你很确定
                continue

        # 4. 执行写入
        if should_write:
            print(f"🔧 处理: {filename}")
            print(f"   原因: {reason}")

            if write_exif(exiftool, file_path, file_date_str):
                try:
                    shutil.move(file_path, os.path.join(target_folder, filename))
                    print(f"   ✅ 写入成功 -> {os.path.basename(target_folder)}")
                    stats[stats_key] += 1
                except Exception as e:
                    print(f"   ❌ 移动失败: {e}")
            else:
                print("   ❌ ExifTool 写入失败")

    print("------------------------------------------------")
    print("📊 检查报告")
    print(f"🆕 新增EXIF (fixed_new):       {stats['new']}")
    print(f"🩹 纠正错误 (fixed_corrected): {stats['corrected']}")
    print(f"✅ 验证正确 (verified_ok):     {stats['verified']}")
    print(f"❓ 无法识别 (原地不动):        {stats['unknown']}")
    print("------------------------------------------------")


if __name__ == "__main__":
    main()
