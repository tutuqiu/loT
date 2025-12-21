"""
主程序入口
"""
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt5.QtCore import Qt
from pages.home import HomePage
from pages.publisher import PublisherPage
from pages.viewer import ViewerPage


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("IoT 数据发布订阅及分析系统")
        self.setMinimumSize(1200, 800)
        
        # 创建堆叠窗口
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # 创建页面
        self.home_page = HomePage()
        self.publisher_page = PublisherPage()
        self.viewer_page = ViewerPage()
        
        # 设置主窗口引用（用于页面切换）
        self.home_page.main_window = self
        self.publisher_page.main_window = self
        self.viewer_page.main_window = self
        
        # 添加到堆叠窗口
        self.stacked_widget.addWidget(self.home_page)
        self.stacked_widget.addWidget(self.publisher_page)
        self.stacked_widget.addWidget(self.viewer_page)
        
        # 显示首页
        self.stacked_widget.setCurrentWidget(self.home_page)
    
    def switch_to_home(self):
        """切换到首页"""
        self.stacked_widget.setCurrentWidget(self.home_page)
    
    def switch_to_publisher(self):
        """切换到发布端控制页面"""
        self.stacked_widget.setCurrentWidget(self.publisher_page)
    
    def switch_to_viewer(self):
        """切换到数据查看页面"""
        self.stacked_widget.setCurrentWidget(self.viewer_page)


def main():
    """主函数"""
    try:
        app = QApplication(sys.argv)
        
        # 设置应用样式
        app.setStyle('Fusion')
        
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec_())
    except Exception as e:
        import traceback
        print(f"程序启动失败: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

