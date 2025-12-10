import json
import os
from datetime import datetime

import requests


# 获取文件信息
class photographListDownload:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
        }
        self.path = "./json/"
        self.clienttype = None
        self.bdstoken = None
        self.need_thumbnail = None
        self.need_filter_hidden = None
        self.flag = True
        self.total_photos = 0  # 记录总共爬取的照片数
        self.filter_date = None  # 过滤日期
        self.date_mode = None  # 日期过滤模式: 'before' 或 'after'
        self.skipped_photos = 0  # 跳过的照片数

    def save_json(self, photo_list):
        for photo in photo_list:
            try:
                # 日期过滤
                if self.filter_date and "extra_info" in photo and "date_time" in photo["extra_info"]:
                    photo_date_str = photo["extra_info"]["date_time"][:10]  # 获取日期部分 YYYY:MM:DD
                    photo_date = datetime.strptime(photo_date_str.replace(':', '-'), '%Y-%m-%d')
                    
                    # 根据模式过滤
                    if self.date_mode == 'before' and photo_date >= self.filter_date:
                        self.skipped_photos += 1
                        continue
                    elif self.date_mode == 'after' and photo_date <= self.filter_date:
                        self.skipped_photos += 1
                        continue
                
                # 安全处理文件路径，path前12个字符是"/mnt/yike/fs"前缀
                file_name = os.path.join(self.path, photo["path"][12:] + ".json")
                with open(file_name, "w", encoding="utf-8") as f:
                    json.dump(photo, f, ensure_ascii=False, indent=4)
                self.total_photos += 1
            except Exception as e:
                print(f"保存文件失败: {file_name}, 错误: {e}")

    def crawler(self, URL):
        try:
            response = requests.get(URL, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            photo_list = data.get("list", [])
            if not photo_list:  # 爬取完毕
                self.flag = False
                return None
            
            print(f"获取到 {len(photo_list)} 张照片，累计: {self.total_photos + len(photo_list)}")
            self.save_json(photo_list)

            cursor = data.get("cursor")
            return cursor
        except requests.RequestException as e:
            print(f"网络请求失败: {e}")
            self.flag = False
            return None
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            self.flag = False
            return None
        except Exception as e:
            print(f"未知错误: {e}")
            self.flag = False
            return None

    def func(self):
        URL = f"https://photo.baidu.com/youai/file/v1/list?clienttype={self.clienttype}&bdstoken={self.bdstoken}&need_thumbnail={self.need_thumbnail}&need_filter_hidden={self.need_filter_hidden}"
        cursor = self.crawler(URL)
        while self.flag and cursor:
            URL = f"https://photo.baidu.com/youai/file/v1/list?clienttype={self.clienttype}&bdstoken={self.bdstoken}&cursor={cursor}&need_thumbnail={self.need_thumbnail}&need_filter_hidden={self.need_filter_hidden}"
            cursor = self.crawler(URL)

    def start(self):
        try:
            with open("settings.json", 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            self.clienttype = json_data["clienttype"]
            self.bdstoken = json_data["bdstoken"]
            self.need_thumbnail = json_data["need_thumbnail"]
            self.need_filter_hidden = json_data["need_filter_hidden"]
            self.headers["Cookie"] = json_data["Cookie"]
            
            # 读取日期过滤配置（可选）
            if "filter_date" in json_data and json_data["filter_date"]:
                try:
                    self.filter_date = datetime.strptime(json_data["filter_date"], '%Y-%m-%d')
                    self.date_mode = json_data.get("date_mode", "before")  # 默认为before
                    print(f"日期过滤已启用: 只获取 {self.filter_date.strftime('%Y-%m-%d')} {'之前' if self.date_mode == 'before' else '之后'} 的照片")
                except ValueError:
                    print("警告: filter_date 格式不正确，应为 YYYY-MM-DD，已忽略日期过滤")

            os.makedirs(self.path, exist_ok=True)

            print("开始获取照片元数据...")
            self.func()
            if self.skipped_photos > 0:
                print(f"\n✓ 元数据获取完成！共获取 {self.total_photos} 张照片的信息，跳过 {self.skipped_photos} 张")
            else:
                print(f"\n✓ 元数据获取完成！共获取 {self.total_photos} 张照片的信息")
        except FileNotFoundError:
            print("错误: settings.json 文件不存在")
        except json.JSONDecodeError as e:
            print(f"错误: settings.json 文件格式不正确 - {e}")
        except KeyError as e:
            print(f"错误: settings.json 缺少必要字段 - {e}")
        except Exception as e:
            print(f"错误: {e}")
if __name__ == "__main__":
    find_photo_list = photographListDownload()
    find_photo_list.start()