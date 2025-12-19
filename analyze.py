import os
import sys
import re
from PIL import Image, ExifTags
from datetime import datetime

# 定义需要扫描的扩展名
VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.tiff'}

# EXIF Tag ID for DateTimeOriginal (拍摄时间)
TAG_DATETIME_ORIGINAL = 36867

def get_exif_date(file_path):
    """尝试读取图片的 EXIF 拍摄时间"""
    try:
        img = Image.open(file_path)
        exif_data = img._getexif()
        if not exif_data:
            return None
        
        # 获取拍摄时间
        date_str = exif_data.get(TAG_DATETIME_ORIGINAL)
        return date_str  # 格式通常是 "YYYY:MM:DD HH:MM:SS"
    except Exception:
        return None

def analyze_filename(filename):
    """分析文件名特征"""
    # 匹配微信/Unix毫秒时间戳 (13位数字)
    if re.search(r'wx_camera_(\d{13})', filename) or re.search(r'mmexport(\d{13})', filename):
        return "WeChat/UnixTimestamp"
    # 匹配标准年月日 (如 IMG_20231201)
    if re.search(r'20\d{2}[-_]?\d{2}[-_]?\d{2}', filename):
        return "DateInFilename"
    return "Unknown"

def scan_directory(directory):
    print(f"--- 正在分析目录: {directory} ---\n")
    
    stats = {
        "total": 0,
        "valid_exif": 0,
        "missing_exif": 0,
        "fixable_wechat": 0,
        "fixable_filename": 0,
        "hopeless": 0
    }

    # 遍历目录
    for root, _, files in os.walk(directory):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in VALID_EXTENSIONS:
                continue

            stats["total"] += 1
            file_path = os.path.join(root, file)
            
            # 1. 检查 EXIF
            exif_date = get_exif_date(file_path)
            
            if exif_date:
                # 有 EXIF，不需要处理
                stats["valid_exif"] += 1
                # print(f"[OK] {file} -> {exif_date}") # 想看详细日志取消注释
            else:
                stats["missing_exif"] += 1
                
                # 2. 如果没 EXIF，分析有没有救
                file_type = analyze_filename(file)
                
                if file_type == "WeChat/UnixTimestamp":
                    stats["fixable_wechat"] += 1
                    print(f"[待修复-微信] {file}")
                elif file_type == "DateInFilename":
                    stats["fixable_filename"] += 1
                    print(f"[待修复-文件名] {file}")
                else:
                    stats["hopeless"] += 1
                    print(f"[警告-无时间] {file}")

    # --- 输出报告 ---
    print("\n" + "="*30)
    print(" 📊 EXIF 分析报告")
    print("="*30)
    print(f"📂 扫描文件总数:    {stats['total']}")
    print(f"✅ 正常 (有EXIF):    {stats['valid_exif']}")
    print(f"❌ 异常 (无EXIF):    {stats['missing_exif']}")
    print("-" * 30)
    print(" 🛠️  修复建议:")
    print(f"   - 微信/时间戳文件: {stats['fixable_wechat']} 个 (可用 exiftool 提取)")
    print(f"   - 文件名含日期:    {stats['fixable_filename']} 个 (可用 exiftool 猜测)")
    print(f"   - 完全无法识别:    {stats['hopeless']} 个 (可能需要手动处理)")
    print("="*30)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 analyze_exif.py <你的图片文件夹路径>")
    else:
        target_dir = sys.argv[1]
        scan_directory(target_dir)