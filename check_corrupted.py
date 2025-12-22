import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image

# ================= 配置区域 =================
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tiff", ".gif", ".bmp"}
MAX_WORKERS = 16  # 线程数
# ===========================================


def check_file_integrity(file_path):
    """检查文件是否损坏"""
    try:
        with Image.open(file_path) as img:
            img.verify()
        with Image.open(file_path) as img:
            img.load()
        return True, None
    except Exception as e:
        return False, str(e)


def check_single_file(file_info):
    """检查单个文件(用于多线程)"""
    file_path, file_name = file_info
    is_ok, error = check_file_integrity(file_path)
    return {
        "path": file_path,
        "name": file_name,
        "is_ok": is_ok,
        "error": error
    }


def scan_directory(directory):
    """扫描目录检测损坏文件(多线程版)"""
    print(f"🔍 开始扫描: {directory}")
    print(f"⚙️  使用 {MAX_WORKERS} 个线程并发检查\n")
    
    # 收集所有文件
    file_list = []
    for root, _, files in os.walk(directory):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in VALID_EXTENSIONS:
                file_path = os.path.join(root, file)
                file_list.append((file_path, file))
    
    if not file_list:
        print("❌ 未找到图片文件")
        return
    
    print(f"📂 找到 {len(file_list)} 个文件,开始检查...\n")
    
    stats = {"total": len(file_list), "ok": 0, "corrupted": 0}
    corrupted_files = []
    print_lock = threading.Lock()
    
    # 多线程检查
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_single_file, f): f for f in file_list}
        
        for future in as_completed(futures):
            result = future.result()
            
            with print_lock:
                if result["is_ok"]:
                    print(f"✅ {result['name']}")
                    stats["ok"] += 1
                else:
                    print(f"❌ {result['name']} - 损坏")
                    stats["corrupted"] += 1
                    corrupted_files.append({
                        "path": result["path"],
                        "name": result["name"],
                        "error": result["error"]
                    })
    
    # 输出结果
    print("\n" + "=" * 60)
    print(" 📊 扫描结果")
    print("=" * 60)
    print(f" 总文件数: {stats['total']}")
    print(f" 正常文件: {stats['ok']}")
    print(f" 损坏文件: {stats['corrupted']}")
    print("=" * 60)
    
    if corrupted_files:
        print("\n❌ 损坏文件列表:\n")
        for item in corrupted_files:
            print(f"  📁 {item['name']}")
            print(f"     路径: {item['path']}")
            print(f"     错误: {item['error']}\n")
        
        # 询问是否导出列表
        export = input("是否导出损坏文件列表到 corrupted_list.txt? (y/n): ").strip().lower()
        if export == 'y':
            output_file = os.path.join(directory, "corrupted_list.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"损坏文件列表 - 共 {stats['corrupted']} 个\n")
                f.write("=" * 60 + "\n\n")
                for item in corrupted_files:
                    f.write(f"文件名: {item['name']}\n")
                    f.write(f"路径: {item['path']}\n")
                    f.write(f"错误: {item['error']}\n\n")
            print(f"✅ 已导出到: {output_file}")
    else:
        print("\n✨ 太棒了! 所有文件都完好无损!")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        path = input("请输入要检查的文件夹路径 (可直接拖入): ").strip('"')
        if path and os.path.exists(path):
            scan_directory(path)
        else:
            print("❌ 路径无效")
    else:
        scan_directory(sys.argv[1])
    
    input("\n按回车键退出...")
