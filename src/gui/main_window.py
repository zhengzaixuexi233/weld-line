"""
GUI主窗口模块
"""
import cv2
import numpy as np
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFileDialog, QStatusBar, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
from typing import Optional

from .controls import ControlPanel
from ..core.detector import WeldDetector
from ..input_sources import ImageSource, VideoSource, CameraSource
from ..config.manager import ConfigManager
from ..utils.visualization import draw_detections


class MainWindow(QMainWindow):
    def __init__(self, config_manager=None):
        super().__init__()
        self.config_manager = config_manager or ConfigManager()
        self.detector = WeldDetector()
        self.current_source = None
        self.is_detecting = False
        self._init_ui()
        self._load_config()
        self._setup_timer()
    
    def _init_ui(self):
        self.setWindowTitle("焊缝识别系统")
        self.setMinimumSize(1200, 800)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        display_layout = QVBoxLayout()
        self.original_label = QLabel("原始图像")
        self.original_label.setAlignment(Qt.AlignCenter)
        self.original_label.setMinimumSize(400, 300)
        self.original_label.setStyleSheet("border: 1px solid gray;")
        
        self.result_label = QLabel("检测结果")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setMinimumSize(400, 300)
        self.result_label.setStyleSheet("border: 1px solid gray;")
        
        display_layout.addWidget(self.original_label)
        display_layout.addWidget(self.result_label)
        
        self.control_panel = ControlPanel()
        self.control_panel.setFixedWidth(300)
        
        self.control_panel.detect_clicked.connect(self._on_detect_clicked)
        self.control_panel.source_changed.connect(self._on_source_changed)
        self.control_panel.param_changed.connect(self._on_param_changed)
        self.control_panel.file_button.clicked.connect(self._on_file_select)
        
        main_layout.addLayout(display_layout)
        main_layout.addWidget(self.control_panel)
        self.statusBar().showMessage("就绪")
    
    def _load_config(self):
        params = {
            "blur_kernel_size": self.config_manager.get("preprocessing.blur_kernel_size", 5),
            "canny_low": self.config_manager.get("detection.canny_low", 50),
            "canny_high": self.config_manager.get("detection.canny_high", 150),
            "hough_threshold": self.config_manager.get("detection.hough_threshold", 50),
            "min_line_length": self.config_manager.get("detection.min_line_length", 50),
        }
        self.control_panel.set_params(params)
    
    def _setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self._process_frame)
    
    @pyqtSlot()
    def _on_detect_clicked(self):
        if self.is_detecting:
            self.stop_detection()
        else:
            self.start_detection()
    
    @pyqtSlot(str)
    def _on_source_changed(self, source):
        self.stop_detection()
        if source == "camera":
            self.current_source = CameraSource()
    
    @pyqtSlot(str, object)
    def _on_param_changed(self, name, value):
        param_map = {
            "模糊核大小": "blur_kernel_size",
            "Canny低阈值": "canny_low",
            "Canny高阈值": "canny_high",
            "霍夫阈值": "hough_threshold",
            "最小长度": "min_line_length"
        }
        param_name = param_map.get(name)
        if param_name:
            self.detector.update_params(**{param_name: value})
    
    @pyqtSlot()
    def _on_file_select(self):
        current_source = self.control_panel.source_combo.currentText()
        if current_source == "视频文件":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择视频文件", "",
                "视频文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*)")
            if file_path:
                self.current_source = VideoSource(file_path)
                self.statusBar().showMessage(f"已加载视频: {file_path}")
        elif current_source == "图像文件":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择图像文件", "",
                "图像文件 (*.jpg *.jpeg *.png *.bmp);;所有文件 (*)")
            if file_path:
                self.current_source = ImageSource(file_path)
                self.statusBar().showMessage(f"已加载图像: {file_path}")
    
    def start_detection(self):
        if self.current_source is None:
            QMessageBox.warning(self, "警告", "请先选择输入源")
            return
        if not self.current_source.is_opened():
            if isinstance(self.current_source, CameraSource):
                if not self.current_source.open():
                    QMessageBox.critical(self, "错误", "无法打开摄像头")
                    return
        self.is_detecting = True
        self.control_panel.detect_button.setText("停止检测")
        self.statusBar().showMessage("检测中...")
        fps = 30
        if isinstance(self.current_source, VideoSource):
            fps = self.current_source.get_fps()
        self.timer.start(int(1000 / fps))
    
    def stop_detection(self):
        self.is_detecting = False
        self.timer.stop()
        self.control_panel.detect_button.setText("开始检测")
        self.statusBar().showMessage("已停止")
    
    def _process_frame(self):
        if not self.is_detecting or self.current_source is None:
            return
        frame = self.current_source.get_frame()
        if frame is None:
            self.stop_detection()
            return
        detections, processed, edges = self.detector.detect(frame)
        result_frame = draw_detections(frame, detections)
        self._display_image(frame, self.original_label)
        self._display_image(result_frame, self.result_label)
        self.statusBar().showMessage(f"检测到 {len(detections)} 条焊缝")
    
    def _display_image(self, image, label):
        if len(image.shape) == 2:
            h, w = image.shape
            bytes_per_line = w
            q_image = QImage(image.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
        else:
            h, w, ch = image.shape
            bytes_per_line = ch * w
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(scaled_pixmap)
    
    def closeEvent(self, event):
        self.stop_detection()
        if self.current_source:
            self.current_source.release()
        event.accept()
