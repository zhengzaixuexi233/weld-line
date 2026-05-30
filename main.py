"""
焊缝识别系统主入口

启动GUI应用程序。
"""

import sys
from PyQt5.QtWidgets import QApplication
from src.gui.main_window import MainWindow
from src.config.manager import ConfigManager
from src.utils.paths import app_path


def main():
    """主函数"""
    # 创建应用
    app = QApplication(sys.argv)
    
    # 加载配置
    config_manager = ConfigManager(str(app_path("config", "default.yaml")))
    
    # 创建主窗口
    window = MainWindow(config_manager)
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
