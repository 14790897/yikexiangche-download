import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import QDate, Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from photographDownload import photographDownload
from photographListDownload import photographListDownload


class DownloadThread(QThread):
    """下载线程"""

    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    finished_signal = Signal(bool, str)

    def __init__(self, mode, settings):
        super().__init__()
        self.mode = mode  # 'metadata' 或 'download'
        self.settings = settings

    def run(self):
        try:
            if self.mode == "metadata":
                self.download_metadata()
            else:
                self.download_photos()
            self.finished_signal.emit(True, "完成！")
        except Exception as e:
            self.finished_signal.emit(False, f"错误: {str(e)}")

    def download_metadata(self):
        """下载元数据"""
        self.log_signal.emit("开始获取照片元数据...")

        # 保存配置
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)

        downloader = photographListDownload()

        # 重定向输出
        original_print = print

        def custom_print(*args, **kwargs):
            message = " ".join(map(str, args))
            self.log_signal.emit(message)

        import builtins

        builtins.print = custom_print

        try:
            downloader.start()
        finally:
            builtins.print = original_print

    def download_photos(self):
        """下载照片"""
        self.log_signal.emit("开始下载照片...")

        # 保存配置
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)

        downloader = photographDownload()

        # 重定向日志
        import logging

        class QtLogHandler(logging.Handler):
            def __init__(self, signal):
                super().__init__()
                self.signal = signal

            def emit(self, record):
                msg = self.format(record)
                self.signal.emit(msg)

        # 清除现有handlers
        downloader.logger.handlers.clear()

        # 添加Qt handler
        qt_handler = QtLogHandler(self.log_signal)
        qt_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        downloader.logger.addHandler(qt_handler)

        downloader.start()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("百度一刻相册下载器 v1.0")
        self.setMinimumSize(1000, 750)

        # 设置图标
        if Path("icon.ico").exists():
            self.setWindowIcon(QIcon("icon.ico"))

        self.download_thread = None
        self.setup_styles()
        self.init_ui()
        self.load_settings()

    def setup_styles(self):
        """设置全局样式"""
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #4285f4;
            }
            QPushButton {
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #3367d6;
            }
            QPushButton:pressed {
                background-color: #2851a3;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
            QPushButton#stop_btn {
                background-color: #ea4335;
            }
            QPushButton#stop_btn:hover {
                background-color: #d33426;
            }
            QPushButton#secondary_btn {
                background-color: #34a853;
            }
            QPushButton#secondary_btn:hover {
                background-color: #2d9248;
            }
            QLineEdit, QTextEdit, QSpinBox, QDateEdit, QComboBox {
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                background-color: white;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDateEdit:focus, QComboBox:focus {
                border: 2px solid #4285f4;
            }
            QProgressBar {
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                text-align: center;
                background-color: white;
                height: 28px;
            }
            QProgressBar::chunk {
                background-color: #4285f4;
                border-radius: 4px;
            }
            QCheckBox {
                spacing: 8px;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #4285f4;
                border-color: #4285f4;
                image: url(none);
            }
            QTabWidget::pane {
                border: none;
                background-color: transparent;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                color: #666666;
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #4285f4;
            }
            QTabBar::tab:hover:!selected {
                background-color: #d0d0d0;
            }
            QLabel {
                font-size: 13px;
                color: #333333;
            }
        """
        )

    def init_ui(self):
        """初始化界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 顶部标题栏
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 10)

        title = QLabel("📷 百度一刻相册下载器")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #4285f4;")
        header_layout.addWidget(title)

        version_label = QLabel("v1.0")
        version_label.setStyleSheet("color: #999999; font-size: 11px;")
        header_layout.addWidget(version_label)

        header_layout.addStretch()

        # GitHub链接
        github_btn = QPushButton("⭐ GitHub")
        github_btn.setObjectName("secondary_btn")
        github_btn.setMaximumWidth(120)
        github_btn.clicked.connect(lambda: os.system("start https://github.com/14790897/yikexiangche-download"))
        header_layout.addWidget(github_btn)

        layout.addWidget(header)

        # 分隔线
        line = QWidget()
        line.setFixedHeight(2)
        line.setStyleSheet("background-color: #e0e0e0;")
        layout.addWidget(line)

        # 标签页
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # 配置页面
        config_tab = self.create_config_tab()
        tab_widget.addTab(config_tab, "⚙️ 配置")

        # 下载页面
        download_tab = self.create_download_tab()
        tab_widget.addTab(download_tab, "📥 下载")

        # 关于页面
        about_tab = self.create_about_tab()
        tab_widget.addTab(about_tab, "ℹ️ 关于")

        # 底部状态栏
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 10, 0, 0)

        self.status_label = QLabel("✓ 就绪")
        self.status_label.setStyleSheet("color: #34a853; font-weight: bold;")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()

        copyright_label = QLabel("© 2025 百度一刻相册下载器")
        copyright_label.setStyleSheet("color: #999999; font-size: 10px;")
        status_layout.addWidget(copyright_label)

        layout.addWidget(status_widget)

    def create_config_tab(self):
        """创建配置页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 基本配置组
        basic_group = QGroupBox("基本配置")
        basic_layout = QVBoxLayout()

        # ClientType
        clienttype_layout = QHBoxLayout()
        clienttype_label = QLabel("ClientType:")
        clienttype_label.setFont(QFont("Microsoft YaHei UI", 10))
        clienttype_layout.addWidget(clienttype_label)
        self.clienttype_input = QSpinBox()
        self.clienttype_input.setValue(70)
        self.clienttype_input.setMinimum(1)
        self.clienttype_input.setMaximum(999)
        clienttype_layout.addWidget(self.clienttype_input)
        clienttype_layout.addStretch()
        basic_layout.addLayout(clienttype_layout)

        # BDSToken
        bdstoken_layout = QHBoxLayout()
        bdstoken_label = QLabel("BDSToken:")
        bdstoken_label.setFont(QFont("Microsoft YaHei UI", 10))
        bdstoken_layout.addWidget(bdstoken_label)
        self.bdstoken_input = QLineEdit()
        self.bdstoken_input.setPlaceholderText("从浏览器开发者工具中获取")
        bdstoken_layout.addWidget(self.bdstoken_input)
        basic_layout.addLayout(bdstoken_layout)

        # Cookie
        cookie_layout = QVBoxLayout()
        cookie_label = QLabel("Cookie:")
        cookie_label.setFont(QFont("Microsoft YaHei UI", 10))
        cookie_layout.addWidget(cookie_label)
        self.cookie_input = QTextEdit()
        self.cookie_input.setPlaceholderText("从浏览器开发者工具中获取完整的Cookie")
        self.cookie_input.setMaximumHeight(80)
        cookie_layout.addWidget(self.cookie_input)
        basic_layout.addLayout(cookie_layout)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # 高级配置组
        advanced_group = QGroupBox("高级配置")
        advanced_layout = QVBoxLayout()

        # 需要缩略图
        thumbnail_layout = QHBoxLayout()
        self.thumbnail_check = QCheckBox("需要缩略图")
        self.thumbnail_check.setChecked(True)
        thumbnail_layout.addWidget(self.thumbnail_check)
        thumbnail_layout.addStretch()
        advanced_layout.addLayout(thumbnail_layout)

        # 过滤隐藏文件
        filter_hidden_layout = QHBoxLayout()
        self.filter_hidden_check = QCheckBox("过滤隐藏文件")
        filter_hidden_layout.addWidget(self.filter_hidden_check)
        filter_hidden_layout.addStretch()
        advanced_layout.addLayout(filter_hidden_layout)

        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)

        # 日期过滤组
        date_group = QGroupBox("日期过滤（可选）")
        date_layout = QVBoxLayout()

        # 启用日期过滤
        self.date_filter_check = QCheckBox("启用日期过滤")
        self.date_filter_check.stateChanged.connect(self.toggle_date_filter)
        date_layout.addWidget(self.date_filter_check)

        # 日期选择
        date_select_layout = QHBoxLayout()
        date_label = QLabel("过滤日期:")
        date_label.setFont(QFont("Microsoft YaHei UI", 10))
        date_select_layout.addWidget(date_label)
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setEnabled(False)
        date_select_layout.addWidget(self.date_input)
        date_layout.addLayout(date_select_layout)

        # 日期模式
        mode_layout = QHBoxLayout()
        mode_label = QLabel("过滤模式:")
        mode_label.setFont(QFont("Microsoft YaHei UI", 10))
        mode_layout.addWidget(mode_label)
        self.date_mode_combo = QComboBox()
        self.date_mode_combo.addItems(["before (之前)", "after (之后)"])
        self.date_mode_combo.setEnabled(False)
        mode_layout.addWidget(self.date_mode_combo)
        mode_layout.addStretch()
        date_layout.addLayout(mode_layout)

        date_group.setLayout(date_layout)
        layout.addWidget(date_group)

        # 按钮
        button_layout = QHBoxLayout()
        save_btn = QPushButton("保存配置")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)

        load_btn = QPushButton("加载配置")
        load_btn.clicked.connect(self.load_settings)
        button_layout.addWidget(load_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        layout.addStretch()

        return widget

    def create_download_tab(self):
        """创建下载页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # 操作按钮组 - 重新设计为水平排列
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setSpacing(10)

        self.metadata_btn = QPushButton("📋 1. 获取元数据")
        self.metadata_btn.setMinimumHeight(40)
        self.metadata_btn.clicked.connect(self.download_metadata)
        btn_layout.addWidget(self.metadata_btn)

        self.download_btn = QPushButton("📥 2. 下载照片")
        self.download_btn.setMinimumHeight(40)
        self.download_btn.clicked.connect(self.download_photos)
        btn_layout.addWidget(self.download_btn)

        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setObjectName("danger_btn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_download)
        btn_layout.addWidget(self.stop_btn)

        open_folder_btn = QPushButton("📁 打开目录")
        open_folder_btn.setObjectName("secondary_btn")
        open_folder_btn.setMinimumHeight(40)
        open_folder_btn.clicked.connect(self.open_download_folder)
        btn_layout.addWidget(open_folder_btn)

        clear_log_btn = QPushButton("🗑️ 清空日志")
        clear_log_btn.setObjectName("secondary_btn")
        clear_log_btn.setMinimumHeight(40)
        clear_log_btn.clicked.connect(self.clear_log)
        btn_layout.addWidget(clear_log_btn)

        layout.addWidget(btn_widget)

        # 进度条和状态
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setSpacing(8)

        self.progress_label = QLabel("📊 等待开始...")
        self.progress_label.setStyleSheet(
            "color: #666666; font-size: 12px; font-weight: bold;"
        )
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(25)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 6px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #4285f4, stop:1 #34a853);
                border-radius: 5px;
            }
        """
        )
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(progress_widget)

        # 日志输出区域
        log_label = QLabel("📝 执行日志")
        log_label.setStyleSheet("font-weight: bold; color: #333333; font-size: 13px;")
        layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setAcceptRichText(True)
        # 设置字体以确保中文正常显示
        log_font = QFont("Microsoft YaHei UI, Consolas, monospace", 10)
        self.log_text.setFont(log_font)
        self.log_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 12px;
                line-height: 1.5;
            }
        """
        )
        layout.addWidget(self.log_text, 1)

        return widget

    def create_about_tab(self):
        """创建关于页面"""
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # 中心容器
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 应用图标和标题
        icon_title_layout = QHBoxLayout()
        icon_title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if Path("icon.png").exists():
            icon_label = QLabel()
            pixmap = QPixmap("icon.png").scaled(
                64,
                64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(pixmap)
            icon_title_layout.addWidget(icon_label)

        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.setSpacing(5)

        app_title = QLabel("百度一刻相册下载器")
        app_title_font = QFont("Microsoft YaHei UI", 24)
        app_title_font.setBold(True)
        app_title.setFont(app_title_font)
        app_title.setStyleSheet("color: #4285f4;")
        title_layout.addWidget(app_title)

        version_label = QLabel("Version 1.0.0")
        version_font = QFont("Microsoft YaHei UI", 10)
        version_label.setFont(version_font)
        version_label.setStyleSheet("color: #999999;")
        title_layout.addWidget(version_label)

        icon_title_layout.addWidget(title_widget)
        center_layout.addLayout(icon_title_layout)

        # 简介
        desc_label = QLabel("一个强大的百度一刻相册批量下载工具")
        desc_font = QFont("Microsoft YaHei UI", 11)
        desc_label.setFont(desc_font)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; margin-top: 10px;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(desc_label)

        layout.addWidget(center_widget)

        # 功能特性
        features_group = QGroupBox("✨ 功能特性")
        features_layout = QVBoxLayout()
        features_layout.setSpacing(8)
        features = [
            "📥 批量下载百度一刻相册照片",
            "📅 支持按日期过滤照片",
            "⚡ 32线程并发下载，速度快",
            "🔄 断点续传，支持暂停恢复",
            "✅ MD5文件完整性校验",
            "📊 实时进度显示和日志记录",
        ]
        for feature in features:
            label = QLabel(feature)
            label.setWordWrap(True)
            label.setMinimumHeight(30)
            label_font = QFont("Microsoft YaHei UI", 10)
            label.setFont(label_font)
            label.setStyleSheet(
                "padding: 8px; background-color: #f9f9f9; border-radius: 4px;"
            )
            features_layout.addWidget(label)
        features_group.setLayout(features_layout)
        layout.addWidget(features_group)

        # 快速开始
        guide_group = QGroupBox("🚀 快速开始")
        guide_layout = QVBoxLayout()
        guide_layout.setSpacing(8)
        steps = [
            "1️⃣ 在「配置」页面填写 BDSToken 和 Cookie",
            "2️⃣ （可选）设置日期过滤条件",
            "3️⃣ 点击「保存配置」",
            "4️⃣ 在「下载」页面点击「获取元数据」",
            "5️⃣ 等待完成后点击「下载照片」",
        ]
        for step in steps:
            label = QLabel(step)
            label.setWordWrap(True)
            label.setMinimumHeight(30)
            label_font = QFont("Microsoft YaHei UI", 10)
            label.setFont(label_font)
            label.setStyleSheet(
                "padding: 8px; background-color: #f9f9f9; border-radius: 4px;"
            )
            guide_layout.addWidget(label)
        guide_group.setLayout(guide_layout)
        layout.addWidget(guide_group)

        # 底部信息
        layout.addStretch()

        footer_widget = QWidget()
        footer_layout = QVBoxLayout(footer_widget)
        footer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.setSpacing(5)

        copyright_label = QLabel("© 2025 百度一刻相册下载器")
        copyright_label.setStyleSheet("color: #999999; font-size: 11px;")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(copyright_label)

        tech_label = QLabel("基于 Python + PySide6 构建")
        tech_label.setStyleSheet("color: #cccccc; font-size: 10px;")
        tech_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(tech_label)

        layout.addWidget(footer_widget)
        
        # 将内容widget设置到滚动区域
        scroll.setWidget(widget)
        
        return scroll

    def toggle_date_filter(self, state):
        """切换日期过滤"""
        enabled = state == 2  # Qt.Checked
        self.date_input.setEnabled(enabled)
        self.date_mode_combo.setEnabled(enabled)

    def get_settings(self):
        """获取当前配置"""
        settings = {
            "clienttype": self.clienttype_input.value(),
            "bdstoken": self.bdstoken_input.text(),
            "need_thumbnail": 1 if self.thumbnail_check.isChecked() else 0,
            "need_filter_hidden": 1 if self.filter_hidden_check.isChecked() else 0,
            "Cookie": self.cookie_input.toPlainText().strip(),
        }

        # 日期过滤
        if self.date_filter_check.isChecked():
            settings["filter_date"] = self.date_input.date().toString("yyyy-MM-dd")
            settings["date_mode"] = (
                "before" if self.date_mode_combo.currentIndex() == 0 else "after"
            )
        else:
            settings["filter_date"] = ""
            settings["date_mode"] = "before"

        return settings

    def save_settings(self):
        """保存配置"""
        try:
            settings = self.get_settings()

            # 验证必填字段
            if not settings["bdstoken"] or not settings["Cookie"]:
                QMessageBox.warning(self, "配置不完整", "请填写 BDSToken 和 Cookie")
                return

            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)

            self.append_log("✓ 配置已保存")
            self.update_status("配置已保存", "success")
            QMessageBox.information(self, "成功", "配置已成功保存到 settings.json")
        except Exception as e:
            self.append_log(f"✗ 保存配置失败: {str(e)}")
            self.update_status("保存失败", "error")
            QMessageBox.critical(self, "错误", f"保存配置失败:\n{str(e)}")

    def load_settings(self):
        """加载配置"""
        try:
            if Path("settings.json").exists():
                with open("settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)

                self.clienttype_input.setValue(settings.get("clienttype", 70))
                self.bdstoken_input.setText(settings.get("bdstoken", ""))
                self.cookie_input.setPlainText(settings.get("Cookie", ""))
                self.thumbnail_check.setChecked(settings.get("need_thumbnail", 1) == 1)
                self.filter_hidden_check.setChecked(
                    settings.get("need_filter_hidden", 0) == 1
                )

                if settings.get("filter_date"):
                    self.date_filter_check.setChecked(True)
                    date = QDate.fromString(settings["filter_date"], "yyyy-MM-dd")
                    self.date_input.setDate(date)
                    self.date_mode_combo.setCurrentIndex(
                        0 if settings.get("date_mode") == "before" else 1
                    )

                self.append_log("✓ 配置已加载")
                self.update_status("就绪", "success")
        except Exception as e:
            self.append_log(f"✗ 加载配置失败: {str(e)}")
            self.update_status("加载失败", "error")

    def download_metadata(self):
        """获取元数据"""
        if self.download_thread and self.download_thread.isRunning():
            self.append_log("⚠ 已有任务在运行中...")
            self.update_status("任务运行中", "warning")
            return

        settings = self.get_settings()
        if not settings["bdstoken"] or not settings["Cookie"]:
            self.append_log("✗ 请先配置 BDSToken 和 Cookie")
            self.update_status("配置不完整", "error")
            QMessageBox.warning(
                self, "配置错误", "请先在「配置」页面填写 BDSToken 和 Cookie"
            )
            return

        self.log_text.clear()
        self.metadata_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("📊 正在获取元数据...")
        self.update_status("获取元数据中...", "info")

        self.download_thread = DownloadThread("metadata", settings)
        self.download_thread.log_signal.connect(self.append_log)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        self.download_thread.start()

    def download_photos(self):
        """下载照片"""
        if self.download_thread and self.download_thread.isRunning():
            self.append_log("⚠ 已有任务在运行中...")
            self.update_status("任务运行中", "warning")
            return

        if not Path("./json/").exists() or not list(Path("./json/").glob("*.json")):
            self.append_log("✗ 请先获取照片元数据")
            self.update_status("缺少元数据", "error")
            QMessageBox.warning(
                self, "缺少元数据", "请先点击「获取元数据」按钮获取照片列表"
            )
            return

        settings = self.get_settings()

        self.log_text.clear()
        self.metadata_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("📊 正在下载照片...")
        self.update_status("下载中...", "info")

        self.download_thread = DownloadThread("download", settings)
        self.download_thread.log_signal.connect(self.append_log)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        self.download_thread.start()

    def stop_download(self):
        """停止下载"""
        if self.download_thread and self.download_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "确认停止",
                "确定要停止当前任务吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.download_thread.terminate()
                self.download_thread.wait()
                self.append_log("✗ 用户已停止任务")
                self.update_status("已停止", "warning")
                self.on_download_finished(False, "用户停止")

    def on_download_finished(self, success, message):
        """下载完成"""
        self.metadata_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(100 if success else 0)
        self.progress_label.setText("✓ 任务完成" if success else "✗ 任务失败")

        self.append_log(f"\n{'='*50}")
        self.append_log(message)

        if success:
            self.update_status("任务完成", "success")
            QMessageBox.information(self, "完成", message)
        else:
            self.update_status("任务失败", "error")

    def open_download_folder(self):
        """打开下载目录"""
        folder = Path("./photograph/").absolute()
        if folder.exists():
            os.startfile(folder)
            self.append_log(f"ℹ 已打开目录: {folder}")
            self.update_status("已打开目录", "success")
        else:
            self.append_log("✗ 下载目录不存在")
            self.update_status("目录不存在", "error")
            QMessageBox.warning(self, "目录不存在", "下载目录尚未创建，请先下载照片")

    def append_log(self, message):
        """添加日志，带有颜色格式化"""
        from html import escape

        # 根据消息内容添加颜色
        if "✓" in message or "成功" in message or "完成" in message:
            color = "#34a853"  # 绿色
        elif "✗" in message or "错误" in message or "失败" in message:
            color = "#ea4335"  # 红色
        elif "⚠" in message or "警告" in message:
            color = "#fbbc04"  # 黄色
        elif "ℹ" in message or "开始" in message:
            color = "#4285f4"  # 蓝色
        else:
            color = "#d4d4d4"  # 默认白色

        # HTML转义，防止中文被截断
        escaped_msg = escape(message)
        # 格式化消息
        formatted_msg = f'<span style="color: {color};">{escaped_msg}</span>'
        self.log_text.append(formatted_msg)

        # 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self.append_log("ℹ 日志已清空")

    def update_status(self, message, status_type="info"):
        """更新状态栏"""
        icons = {"success": "✓", "error": "✗", "warning": "⚠", "info": "ℹ"}
        colors = {
            "success": "#34a853",
            "error": "#ea4335",
            "warning": "#fbbc04",
            "info": "#4285f4",
        }

        icon = icons.get(status_type, "ℹ")
        color = colors.get(status_type, "#666666")

        self.status_label.setText(f"{icon} {message}")
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")


def main():
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
