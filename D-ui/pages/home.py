"""
首页模块
"""
import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QPixmap, QPalette


class HomePage(QWidget):
    """首页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.background_labels = []
        self.init_ui()
    
    def init_ui(self):
        # 使用布局方式，更安全
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
            }
        """)
        
        # 获取资源路径
        script_dir = Path(__file__).resolve().parent.parent
        resources_dir = script_dir / "resources"
        
        # 添加背景图片（使用绝对定位，但作为子控件）
        self.add_background_images(resources_dir)
        
        # 使用布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 顶部空白
        main_layout.addStretch(3)
        
        # 标题容器（居中）
        title_container = QWidget()
        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setAlignment(Qt.AlignCenter)  # 居中对齐
        
        title = QLabel("某区域温度 / 湿度 / 气压数据\n发布订阅及分析处理系统")
        title_font = QFont("Microsoft YaHei", 54, QFont.Bold)
        title.setFont(title_font)
        title.setStyleSheet("""
            QLabel {
                color: #333333;
                line-height: 1.75;
                background-color: transparent;
            }
        """)
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignCenter)  # 文本居中对齐
        title_layout.addWidget(title)
        title_container.setLayout(title_layout)
        main_layout.addWidget(title_container)
        
        # 中间空白
        main_layout.addStretch(2)
        
        # 按钮容器（居中）
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(80)
        buttons_layout.setAlignment(Qt.AlignCenter)  # 居中对齐
        
        # 发布端按钮
        btn_publisher = QPushButton("发布端")
        btn_publisher.setMinimumSize(200, 60)
        btn_publisher.setFont(QFont("Microsoft YaHei", 26, QFont.Bold))
        btn_publisher.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 101, 167, 1);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: rgb(189, 79, 129);
            }
            QPushButton:pressed {
                background-color: rgb(160, 60, 100);
            }
        """)
        buttons_layout.addWidget(btn_publisher)
        
        # 订阅端按钮
        btn_viewer = QPushButton("订阅端")
        btn_viewer.setMinimumSize(200, 60)
        btn_viewer.setFont(QFont("Microsoft YaHei", 26, QFont.Bold))
        btn_viewer.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 101, 167, 1);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: rgb(189, 79, 129);
            }
            QPushButton:pressed {
                background-color: rgb(160, 60, 100);
            }
        """)
        buttons_layout.addWidget(btn_viewer)
        
        buttons_container.setLayout(buttons_layout)
        main_layout.addWidget(buttons_container)
        
        # 底部空白
        main_layout.addStretch(3)
        
        self.setLayout(main_layout)
        
        # 连接信号
        btn_publisher.clicked.connect(self.on_publisher_clicked)
        btn_viewer.clicked.connect(self.on_viewer_clicked)
        
        # 保存引用
        self.title_label = title
        self.btn_publisher = btn_publisher
        self.btn_viewer = btn_viewer
    
    def add_background_images(self, resources_dir):
        """添加背景图片"""
        # 背景图片配置（位置和大小，参考Vue CSS）
        bg_configs = [
            {"file": "background1.png", "x": 0.10, "y": -0.30, "width": 500, "height": None},
            {"file": "background2.png", "x": 0.34, "y": 0.09, "width": 90, "height": None},
            {"file": "background3.png", "x": 0.95, "y": -0.17, "width": 250, "height": None},
            {"file": "background4.png", "x": -0.10, "y": 0.50, "width": 700, "height": None},
            {"file": "background5.png", "x": 0.90, "y": 0.10, "width": 650, "height": None},
        ]
        
        # 如果资源目录不存在，跳过背景图片加载
        if not resources_dir.exists():
            print(f"警告: 资源目录不存在: {resources_dir}")
            return
        
        for config in bg_configs:
            try:
                bg_path = resources_dir / config["file"]
                if bg_path.exists():
                    label = QLabel(self)
                    pixmap = QPixmap(str(bg_path))
                    if pixmap.isNull():
                        print(f"警告: 无法加载图片 {bg_path}")
                        label.deleteLater()
                        continue
                    if config["height"]:
                        pixmap = pixmap.scaled(config["width"], config["height"], 
                                              Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    else:
                        pixmap = pixmap.scaledToWidth(config["width"], Qt.SmoothTransformation)
                    label.setPixmap(pixmap)
                    label.setScaledContents(False)
                    label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                    label.lower()  # 将背景图片放在最底层
                    self.background_labels.append((label, config))
            except Exception as e:
                print(f"加载背景图片 {config['file']} 时出错: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    def resizeEvent(self, event):
        """窗口大小改变时重新定位背景图片"""
        super().resizeEvent(event)
        width = self.width()
        height = self.height()
        
        # 如果窗口大小无效，使用默认值
        if width <= 0:
            width = 1200
        if height <= 0:
            height = 800
        
        # 更新背景图片位置
        for label, config in self.background_labels:
            x = int(width * config["x"])
            y = int(height * config["y"])
            label.move(x, y)
    
    def on_publisher_clicked(self):
        """跳转到发布端控制页面"""
        if hasattr(self, 'main_window') and self.main_window:
            self.main_window.switch_to_publisher()
    
    def on_viewer_clicked(self):
        """跳转到数据查看页面"""
        if hasattr(self, 'main_window') and self.main_window:
            self.main_window.switch_to_viewer()

