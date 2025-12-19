import os
import sys
import re
import shutil
import subprocess
from PIL import Image
from datetime import datetime

# ================= 配置区域 =================
VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.tiff'}
TAG_DATETIME_ORIGINAL = 36867
# ===========================================

def get_exiftool_path():
    """
    在 Windows 上查找 exiftool.exe
    1. 先看系统 PATH 里有没有
    2. 再看脚本当前目录下有没有
    """
    # 检查全局命令
    if shutil.which("exiftool"):
        return "exiftool"
    
    # 检查当前脚本目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_exiftool = os.path.join(script_dir, "exiftool.exe")
    if os.path.exists(local_exiftool):
        return local_exiftool
        
    return None

def get_exif_date(file_path):
    """读取 EXIF 时间"""
    try:
        img = Image.open(file_path)
        exif_data = img._getexif()
        if not exif_data:
            return None
        return exif_data.get(TAG_DATETIME_ORIGINAL)
    except Exception:
        return None

def parse_date_from_filename(filename):
    """
    [修正版] 分析文件名，返回 (类型, 格式化后的时间字符串)
    增加对非法时间戳的过滤，防止脚本崩溃
    """
    # 1. 匹配 13位(毫秒) 或 10位(秒) 的数字，且必须以 1 开头
    # 这里的正则改为直接寻找连续的13位或10位数字，且第一位是1
    # 这样能正确提取 1630924094748 而不会切分成 6309...
    ts_matches = re.findall(r'(1\d{9,12})', filename)
    
    for ts_str in ts_matches:
        try:
            timestamp = int(ts_str)
            
            # 如果是13位，认为是毫秒，除以1000
            if len(ts_str) == 13:
                timestamp /= 1000.0
            
            # 【安全检查】
            # 过滤掉太离谱的时间，比如小于1990年或大于2030年
            # 这样能有效防止非时间戳的数字串混入
            if timestamp < 631152000 or timestamp > 1893456000:
                continue 

            dt_obj = datetime.fromtimestamp(timestamp)
            return "Timestamp", dt_obj.strftime("%Y:%m:%d %H:%M:%S")
        except (ValueError, OSError, OverflowError):
            # 如果转换失败（比如数字太大导致越界），直接忽略，不要让脚本崩溃
            continue

    # 2. 匹配标准年月日 (YYYYMMDD 或 YYYY-MM-DD)
    date_match = re.search(r'(20\d{2})[-_]?(\d{2})[-_]?(\d{2})', filename)
    if date_match:
        try:
            y, m, d = date_match.groups()
            # 简单验证月份和日期是否合法
            if 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
                return "DateString", f"{y}:{m}:{d} 12:00:00"
        except Exception:
            pass

    return "Unknown", None

def write_exif_date(exiftool_path, file_path, date_str):
    """调用 exiftool 写入时间 (调试版)"""
    try:
        cmd = [
            exiftool_path,
            '-overwrite_original',
            # '-q', # 注释掉静默模式，我们要看报错
            f'-DateTimeOriginal={date_str}',
            f'-CreateDate={date_str}', 
            file_path
        ]
        # 增加 text=True 以便直接读取文本报错
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            print(f"\n🚨 [ExifTool 报错] 文件: {os.path.basename(file_path)}")
            print(f"   错误信息: {result.stderr.strip()}") # 打印出具体原因
            return False
            
        return True
    except Exception as e:
        print(f"\n🚨 [Python 报错] {e}")
        return False

def move_file(src_path, dest_folder):
    """移动并重命名防冲突"""
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    
    filename = os.path.basename(src_path)
    dest_path = os.path.join(dest_folder, filename)
    
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(dest_path):
        dest_path = os.path.join(dest_folder, f"{base}_{counter}{ext}")
        counter += 1
        
    shutil.move(src_path, dest_path)
    return dest_path

def process_directory(directory):
    exiftool_cmd = get_exiftool_path()
    if not exiftool_cmd:
        print("❌ 错误: 找不到 exiftool.exe")
        print("请下载 exiftool(-k).exe，重命名为 exiftool.exe")
        print("然后把它放在 C:\\Windows 目录下，或者和本脚本放在一起。")
        return

    print(f"🔧 使用 ExifTool: {exiftool_cmd}")
    print(f"🚀 正在扫描: {directory}")
    
    dir_wechat = os.path.join(directory, "fixed_wechat")
    dir_date = os.path.join(directory, "fixed_date")
    dir_review = os.path.join(directory, "manual_review")

    stats = {"total": 0, "fixed_wechat": 0, "fixed_date": 0, "moved_review": 0}

    for root, _, files in os.walk(directory):
        if any(x in root for x in ["fixed_wechat", "fixed_date", "manual_review"]):
            continue

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in VALID_EXTENSIONS:
                continue

            stats["total"] += 1
            file_path = os.path.join(root, file)

            # 1. 检查 EXIF
            if get_exif_date(file_path):
                continue

            # 2. 分析文件名
            print(f"处理: {file} ...", end="", flush=True)
            f_type, date_str = parse_date_from_filename(file)

            if f_type != "Unknown" and date_str:
                # 3. 修复
                if write_exif_date(exiftool_cmd, file_path, date_str):
                    target_dir = dir_wechat if f_type == "WeChat" else dir_date
                    move_file(file_path, target_dir)
                    print(f" ✅ 修复成功 -> {f_type}")
                    if f_type == "WeChat": stats["fixed_wechat"] += 1
                    else: stats["fixed_date"] += 1
                else:
                    print(" ❌ 写入失败")
            else:
                # 4. 无法识别
                move_file(file_path, dir_review)
                stats["moved_review"] += 1
                print(" ⚠️  无法识别 -> 待人工审核")

    print("\n" + "="*40)
    print(" 🎉 完成！")
    print(f" 微信修复: {stats['fixed_wechat']}")
    print(f" 日期修复: {stats['fixed_date']}")
    print(f" 人工审核: {stats['moved_review']}")
    print("="*40)
    input("按回车键退出...") # 防止双击运行后窗口直接消失

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # 如果用户直接双击脚本，提示输入路径
        path = input("请输入图片文件夹路径 (可直接拖入文件夹): ").strip('"')
        if path:
            process_directory(path)
    else:
        process_directory(sys.argv[1])