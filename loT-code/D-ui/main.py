"""
主程序入口
"""
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from pages.combined import CombinedPage


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("IoT 数据发布订阅及分析系统")
        self.setMinimumSize(1400, 900)
        
        # 直接显示组合页面
        self.combined_page = CombinedPage()
        self.setCentralWidget(self.combined_page)


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
        print(f"程序启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

