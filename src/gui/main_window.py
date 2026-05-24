"""
GUI主窗口模块
"""
import cv2
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFileDialog, QStatusBar, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap, QDragEnterEvent, QDropEvent
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
        self.image_list = []
        self.current_image_index = 0
        self._last_frame = None
        self._last_result = None
        self._last_edges = None
        self.setAcceptDrops(True)
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
        
        self.edges_label = QLabel("边缘图")
        self.edges_label.setAlignment(Qt.AlignCenter)
        self.edges_label.setMinimumSize(400, 300)
        self.edges_label.setStyleSheet("border: 1px solid gray;")
        self.edges_label.hide()
        
        self.drop_overlay = QLabel("拖放图片/视频文件到此处", self)
        self.drop_overlay.setAlignment(Qt.AlignCenter)
        self.drop_overlay.setStyleSheet(
            "background-color: rgba(0, 120, 215, 160);"
            "color: white; font-size: 22px; font-weight: bold;"
            "border: 3px dashed white; border-radius: 12px;")
        self.drop_overlay.hide()

        display_layout.addWidget(self.original_label)
        display_layout.addWidget(self.result_label)
        display_layout.addWidget(self.edges_label)
        
        self.control_panel = ControlPanel()
        self.control_panel.setFixedWidth(380)
        
        self.control_panel.detect_clicked.connect(self._on_detect_clicked)
        self.control_panel.source_changed.connect(self._on_source_changed)
        self.control_panel.param_changed.connect(self._on_param_changed)
        self.control_panel.file_button.clicked.connect(self._on_file_select)
        self.control_panel.prev_image_clicked.connect(self._on_prev_image)
        self.control_panel.next_image_clicked.connect(self._on_next_image)
        self.control_panel.display_option_changed.connect(self._on_display_option_changed)
        
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
            "max_line_gap": self.config_manager.get("detection.max_line_gap", 10),
            "angle_tolerance": self.config_manager.get("detection.angle_tolerance", 15),
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

    @pyqtSlot()
    def _on_prev_image(self):
        if not self.image_list or self.current_image_index <= 0:
            return
        self.current_image_index -= 1
        self._load_image_at_index()
    
    @pyqtSlot()
    def _on_next_image(self):
        if not self.image_list or self.current_image_index >= len(self.image_list) - 1:
            return
        self.current_image_index += 1
        self._load_image_at_index()
    
    def _load_image_at_index(self):
        if not self.image_list or self.current_image_index >= len(self.image_list):
            return
        self.stop_detection()
        img_path = self.image_list[self.current_image_index]
        self.current_source = ImageSource(str(img_path))
        self.statusBar().showMessage(
            f"图片: {img_path.name} ({self.current_image_index + 1}/{len(self.image_list)})")
        self._update_browse_buttons(self.current_image_index > 0, self.current_image_index < len(self.image_list) - 1)
        # 自动显示图片
        frame = self.current_source.get_frame()
        if frame is not None:
            self._display_image(frame, self.original_label)
    
    @pyqtSlot(str, object)
    def _on_param_changed(self, name, value):
        param_map = {
            "模糊核大小": "blur_kernel_size",
            "Canny低阈值": "canny_low",
            "Canny高阈值": "canny_high",
            "霍夫阈值": "hough_threshold",
            "最小长度": "min_line_length",
            "最大线段间隔": "max_line_gap",
            "角度容差": "angle_tolerance"
        }
        param_name = param_map.get(name)
        if param_name:
            self.detector.update_params(**{param_name: value})
    
    @pyqtSlot()
    def _on_display_option_changed(self):
        """显示选项改变时更新面板可见性"""
        options = self.control_panel.get_display_options()
        self.original_label.setVisible(options['show_original'])
        self.result_label.setVisible(options['show_processed'])
        self.edges_label.setVisible(options['show_edges'])
        if self._last_frame is not None:
            if options['show_original']:
                self._display_image(self._last_frame, self.original_label)
            if options['show_processed']:
                self._display_image(self._last_result, self.result_label)
            if options['show_edges']:
                self._display_image(self._last_edges, self.edges_label)
    
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
            default_dir = str(Path(__file__).resolve().parents[3] / "data" / "images")
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择图像文件", default_dir,
                "图像文件 (*.jpg *.jpeg *.png *.bmp);;所有文件 (*)")
            if file_path:
                self.current_source = ImageSource(file_path)
                self.image_list = []
                self.current_image_index = 0
                self._update_browse_buttons(False, False)
                self.statusBar().showMessage(f"已加载图像: {file_path}")
                # 自动显示图片
                frame = self.current_source.get_frame()
                if frame is not None:
                    self._display_image(frame, self.original_label)
    def _update_browse_buttons(self, has_prev, has_next):
        self.control_panel.prev_button.setEnabled(has_prev)
        self.control_panel.next_button.setEnabled(has_next)
    
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
        self._last_frame = frame
        self._last_result = result_frame
        self._last_edges = edges
        options = self.control_panel.get_display_options()
        if options['show_original']:
            self._display_image(frame, self.original_label)
        if options['show_processed']:
            self._display_image(result_frame, self.result_label)
        if options['show_edges']:
            self._display_image(edges, self.edges_label)
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.drop_overlay.resize(self.centralWidget().size())

    # ---------- 拖放支持 ----------

    _SUPPORTED_IMAGE = ImageSource.SUPPORTED_FORMATS
    _SUPPORTED_VIDEO = VideoSource.SUPPORTED_FORMATS

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                suffix = Path(url.toLocalFile()).suffix.lower()
                if suffix in self._SUPPORTED_IMAGE or suffix in self._SUPPORTED_VIDEO:
                    event.acceptProposedAction()
                    self.drop_overlay.show()
                    self.drop_overlay.raise_()
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.drop_overlay.hide()

    def dropEvent(self, event: QDropEvent):
        self.drop_overlay.hide()
        for url in event.mimeData().urls():
            file_path = Path(url.toLocalFile())
            if not file_path.exists():
                continue
            suffix = file_path.suffix.lower()
            if suffix in self._SUPPORTED_IMAGE:
                self.stop_detection()
                self.current_source = ImageSource(str(file_path))
                self._display_image(self.current_source.get_frame(), self.original_label)
                self.control_panel.source_combo.setCurrentText("图像文件")
                self.statusBar().showMessage(f"已拖入图像: {file_path.name}")
                event.acceptProposedAction()
                return
            if suffix in self._SUPPORTED_VIDEO:
                self.stop_detection()
                self.current_source = VideoSource(str(file_path))
                self.control_panel.source_combo.setCurrentText("视频文件")
                self.statusBar().showMessage(f"已拖入视频: {file_path.name}")
                event.acceptProposedAction()
                return
        event.ignore()