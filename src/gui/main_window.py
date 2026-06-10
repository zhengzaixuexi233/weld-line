"""
GUI主窗口模块
"""
import cv2
import numpy as np
from pathlib import Path
import datetime
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFileDialog, QStatusBar, QMessageBox, QSlider, QShortcut, QPushButton,
    QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QPointF, QSizeF, QRectF
from PyQt5.QtGui import QImage, QPixmap, QDragEnterEvent, QDropEvent, QCursor, QPainter
from typing import Optional

from .controls import ControlPanel
from ..core.detector import WeldDetector
from ..input_sources import ImageSource, VideoSource, CameraSource
from ..config.manager import ConfigManager
from ..utils.visualization import draw_detections
from ..utils.paths import app_path

from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import pyqtSignal

class ClickableLabel(QLabel):
    """可点击的QLabel，点击后发射clicked信号"""
    clicked = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._source_pixmap = None
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

    def set_image_pixmap(self, pixmap):
        """保存原始 pixmap，尺寸变化时可重新按控件区域缩放。"""
        self._source_pixmap = pixmap
        self._update_scaled_pixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def clear(self):
        self._source_pixmap = None
        super().clear()

    def _update_scaled_pixmap(self):
        if self._source_pixmap is None or self.width() <= 0 or self.height() <= 0:
            return
        scaled_pixmap = self._source_pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        super().setPixmap(scaled_pixmap)


class ClickableSlider(QSlider):
    """支持点击直接跳转到点击位置的 QSlider"""
    def _value_from_x(self, x):
        return int(self.minimum() + (self.maximum() - self.minimum()) * x / max(1, self.width()))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setValue(self._value_from_x(event.x()))
            self.sliderPressed.emit()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.setValue(self._value_from_x(event.x()))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.sliderReleased.emit()


class ScalableImageLabel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_pixmap = None
        self._zoom_factor = 1.0
        self._dragging = False
        self._last_drag_pos = None
        self._offset = QPointF(0, 0)
        self.setCursor(QCursor(Qt.OpenHandCursor))

    def setPixmap(self, pixmap, preserve_view=False):
        self._original_pixmap = pixmap
        if not preserve_view:
            self._zoom_factor = 1.0
            self._offset = QPointF(0, 0)
        else:
            self._clamp_offset()
        self.update()

    def wheelEvent(self, event):
        if self._original_pixmap is None:
            return
        delta = event.angleDelta().y()
        if delta > 0:
            self._zoom_factor += 0.2
        elif delta < 0:
            self._zoom_factor -= 0.2
        self._zoom_factor = max(1.0, min(3.0, self._zoom_factor))
        self._clamp_offset()
        self.update()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._original_pixmap is not None:
            self._dragging = True
            self._last_drag_pos = event.pos()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and self._last_drag_pos is not None:
            delta = event.pos() - self._last_drag_pos
            self._offset += QPointF(delta)
            self._clamp_offset()
            self._last_drag_pos = event.pos()
            self.update()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self._last_drag_pos = None
            self.setCursor(QCursor(Qt.OpenHandCursor))
            event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._clamp_offset()

    def paintEvent(self, event):
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        scaled_size = self._scaled_size()
        x = (self.width() - scaled_size.width()) / 2 + self._offset.x()
        y = (self.height() - scaled_size.height()) / 2 + self._offset.y()
        painter.drawPixmap(QRectF(x, y, scaled_size.width(), scaled_size.height()), self._original_pixmap, QRectF(self._original_pixmap.rect()))

    def _scaled_size(self):
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return QSizeF(0, 0)
        fit_scale = min(
            self.width() / self._original_pixmap.width(),
            self.height() / self._original_pixmap.height()
        )
        scale = max(0.01, fit_scale) * self._zoom_factor
        return QSizeF(
            self._original_pixmap.width() * scale,
            self._original_pixmap.height() * scale
        )

    def _clamp_offset(self):
        scaled_size = self._scaled_size()
        max_x = max(0, (scaled_size.width() - self.width()) / 2)
        max_y = max(0, (scaled_size.height() - self.height()) / 2)
        x = min(max(self._offset.x(), -max_x), max_x)
        y = min(max(self._offset.y(), -max_y), max_y)
        self._offset = QPointF(x, y)


class MainWindow(QMainWindow):
    def __init__(self, config_manager=None):
        super().__init__()
        self.config_manager = config_manager or ConfigManager()
        self.detector = WeldDetector()
        self.current_source = None
        self.is_detecting = False
        self.is_video_playing = False
        self.image_list = []
        self.current_image_index = 0
        self.video_list = []
        self.current_video_index = 0
        self._last_frame = None
        self._last_result = None
        self._last_edges = None
        self._auto_save = False
        self._vw_original = None
        self._vw_result = None
        self._vw_edges = None
        self._save_session_dir = None
        self._is_drop_action = False  # 标记是否正在执行拖放操作
        self._progress_dragging = False
        self.video_slider = None
        self.video_progress_row = None
        self.video_current_time_label = None
        self.video_total_time_label = None
        self.video_play_btn = None
        self._enlarged_dialog = None
        self.setAcceptDrops(True)
        self._init_ui()
        self._load_config()
        self._setup_timer()
        # 默认初始化摄像头源
        self._on_source_changed("camera")
    
    def _init_ui(self):
        self.setWindowTitle("焊缝识别系统")
        self.setMinimumSize(1240, 800)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        self.display_layout = QVBoxLayout()
        display_layout = self.display_layout
        self.original_label = ClickableLabel("原始图像")
        self.original_label.setAlignment(Qt.AlignCenter)
        self.original_label.setMinimumSize(400, 100)
        self.original_label.setStyleSheet("border: 1px solid gray;")
        self.original_label.clicked.connect(lambda: self._show_enlarged("original"))
        
        self.result_label = ClickableLabel("检测结果")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setMinimumSize(400, 100)
        self.result_label.setStyleSheet("border: 1px solid gray;")
        self.result_label.clicked.connect(lambda: self._show_enlarged("result"))
        
        self.edges_label = ClickableLabel("边缘图")
        self.edges_label.setAlignment(Qt.AlignCenter)
        self.edges_label.setMinimumSize(400, 100)
        self.edges_label.setStyleSheet("border: 1px solid gray;")
        self.edges_label.hide()
        self.edges_label.clicked.connect(lambda: self._show_enlarged("edges"))
        
        self.drop_overlay = QLabel("拖放图片/视频文件到此处", self)
        self.drop_overlay.setAlignment(Qt.AlignCenter)
        self.drop_overlay.setStyleSheet(
            "background-color: rgba(0, 120, 215, 160);"
            "color: white; font-size: 22px; font-weight: bold;"
            "border: 3px dashed white; border-radius: 12px;")
        self.drop_overlay.hide()

        display_layout.addWidget(self.original_label, stretch=1)
        display_layout.addWidget(self.edges_label, stretch=1)
        display_layout.addWidget(self.result_label, stretch=1)
        
        self.control_panel = ControlPanel()
        self.control_panel.setMinimumWidth(400)
        self.control_panel.setMaximumWidth(480)
        self.control_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        self.control_panel.detect_clicked.connect(self._on_detect_clicked)
        self.control_panel.source_changed.connect(self._on_source_changed)
        self.control_panel.param_changed.connect(self._on_param_changed)
        self.control_panel.prev_image_clicked.connect(self._on_prev_image)
        self.control_panel.next_image_clicked.connect(self._on_next_image)
        self.control_panel.display_option_changed.connect(self._on_display_option_changed)
        self.control_panel.reset_params_clicked.connect(self._on_reset_params)
        self.control_panel.profile_changed.connect(self._on_profile_changed)
        self.control_panel.new_profile_clicked.connect(self._on_new_profile)
        self.control_panel.save_profile_clicked.connect(self._on_save_profile)
        self.control_panel.delete_profile_clicked.connect(self._on_delete_profile)
        self.control_panel.auto_save_toggled.connect(self._on_auto_save_toggled)
        self.control_panel.open_saved_folder.connect(self._on_open_saved_folder)
        self.control_panel.camera_changed.connect(self._on_camera_changed)
        self.control_panel.open_source_folder.connect(self._on_open_source_folder)
        # 全局空格键：视频源切换播放，其他源切换检测
        QShortcut(Qt.Key_Space, self).activated.connect(self._toggle_space_action)

        main_layout.addLayout(display_layout, 3)
        main_layout.addWidget(self.control_panel, 1)
        self.statusBar().showMessage("就绪")
    
    @pyqtSlot(bool)
    def _on_auto_save_toggled(self, enabled: bool):
        """自动保存开关"""
        self._auto_save = enabled
        if not enabled:
            self._stop_video_recording()
    
    @pyqtSlot()
    def _on_open_saved_folder(self):
        """打开保存文件夹"""
        import os
        saved_dir = app_path("data", "saved")
        saved_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(saved_dir))
    
    @pyqtSlot(str)
    def _on_open_source_folder(self, source_type: str):
        """打开数据源文件夹"""
        folder_name = "videos" if source_type == "video" else "images"
        folder = app_path("data", folder_name)
        folder.mkdir(parents=True, exist_ok=True)
        import os
        os.startfile(str(folder))
    
    
    @pyqtSlot(int)
    def _on_camera_changed(self, camera_id: int):
        """切换摄像头"""
        self.stop_detection()
        self._clear_display()
        self.preview_timer.stop()
        if self.current_source:
            self.current_source.release()
        self.current_source = CameraSource(camera_id=camera_id)
        if self.current_source.open():
            self.preview_timer.start(33)
            self.statusBar().showMessage(f"已切换到摄像头 {camera_id}")
        else:
            self.statusBar().showMessage(f"无法打开摄像头 {camera_id}")
    
    
    def _load_config(self):
        params = {
            "blur_kernel_size": self.config_manager.get("preprocessing.blur_kernel_size", 5),
            "clahe_clip_limit": self.config_manager.get("preprocessing.clahe_clip_limit", 2.0),
            "canny_low": self.config_manager.get("detection.canny_low", 50),
            "canny_high": self.config_manager.get("detection.canny_high", 150),
            "hough_threshold": self.config_manager.get("detection.hough_threshold", 50),
            "min_line_length": self.config_manager.get("detection.min_line_length", 50),
            "max_line_gap": self.config_manager.get("detection.max_line_gap", 10),
            "angle_tolerance": self.config_manager.get("detection.angle_tolerance", 15),
        }
        self.control_panel.set_params(params)
        # 初始化参数模板列表
        self._refresh_profile_list()
    
    def _setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self._process_frame)
        # 摄像头预览定时器（检测前显示原始画面）
        self.preview_timer = QTimer()
        self.preview_timer.timeout.connect(self._update_camera_preview)

    def _update_camera_preview(self):
        """摄像头预览：检测前显示原始画面"""
        if self.current_source is None or not isinstance(self.current_source, CameraSource):
            return
        frame = self.current_source.get_frame()
        if frame is not None:
            self._display_image(frame, self.original_label)
    
    @pyqtSlot()
    def _on_detect_clicked(self):
        if self.is_detecting:
            self.stop_detection()
        else:
            self.start_detection()
    
    @pyqtSlot(str)
    def _on_source_changed(self, source):
        # 切换源前关闭放大窗口，避免 live_update 访问已失效的源对象
        if getattr(self, "_enlarged_live_timer", None) is not None:
            self._enlarged_live_timer.stop()
            self._enlarged_live_timer = None
        if self._enlarged_dialog is not None:
            self._enlarged_dialog.close()
            self._enlarged_dialog = None
        self.stop_detection()
        self._clear_display()
        self.preview_timer.stop()
        if self.current_source:
            self.current_source.release()
            self.current_source = None
        # 非图片源时禁用浏览按钮
        if source not in ("image", "video"):
            self.control_panel.prev_button.setEnabled(False)
            self.control_panel.next_button.setEnabled(False)
        if source == "camera":
            first_cam = 0
            if self.control_panel.camera_combo.count() > 0:
                first_cam = self.control_panel.camera_combo.itemData(0)
                if first_cam is None or first_cam < 0:
                    first_cam = 0
            self.current_source = CameraSource(camera_id=first_cam)
            # 打开摄像头并开始预览
            if self.current_source.open():
                self.preview_timer.start(33)  # ~30fps 预览
                self.statusBar().showMessage("摄像头已打开，点击「开始检测」进行焊缝检测")
            else:
                self.statusBar().showMessage("无法打开摄像头")
        elif source == "image":
            # 自动扫描 data/images 目录
            images_dir = app_path("data", "images")
            if images_dir.exists():
                self.image_list = ImageSource.list_images(images_dir)
                if self.image_list:
                    self.current_image_index = 0
                    self._load_image_at_index()
                    self.statusBar().showMessage(
                        f"已加载 {len(self.image_list)} 张图片 (目录: {images_dir.name})")
                else:
                    self.statusBar().showMessage(f"data/images 目录为空，请放入图片")
            else:
                 self.statusBar().showMessage("data/images 目录不存在")
        elif source == "video":
            videos_dir = app_path("data", "videos")
            if videos_dir.exists():
                self.video_list = sorted([f for f in videos_dir.iterdir() if f.suffix.lower() in VideoSource.SUPPORTED_FORMATS])
                if self.video_list:
                    self.current_video_index = 0
                    self._load_video_at_index()
                    self.statusBar().showMessage(f"已加载 {len(self.video_list)} 个视频 (目录: {videos_dir.name})")
                else:
                    self.statusBar().showMessage(f"data/videos 目录为空，请放入视频")
            else:
                 self.statusBar().showMessage("data/videos 目录不存在")
        # 视频源：创建进度条；其他源：销毁进度条
        if source == "video":
            self._create_video_progress()
        else:
            self._destroy_video_progress()

        # 视频源：创建进度条后更新进度条范围
        if source == "video" and self.video_slider is not None and isinstance(self.current_source, VideoSource):
            total = self.current_source.frame_count
            if total > 0:
                self.video_slider.setMaximum(total - 1)
                self.video_slider.setValue(0)
                fps_val = self.current_source.get_fps() or 30
                self.video_current_time_label.setText(self._format_time(0))
                self.video_total_time_label.setText(self._format_time(total / fps_val))

    @pyqtSlot()
    def _on_prev_image(self):
        if isinstance(self.current_source, VideoSource):
            if self.current_video_index <= 0:
                return
            self.current_video_index -= 1
            self._load_video_at_index()
            return
        if not self.image_list or self.current_image_index <= 0:
            return
        self.current_image_index -= 1
        self._load_image_at_index()
    
    @pyqtSlot()
    def _on_next_image(self):
        if isinstance(self.current_source, VideoSource):
            if self.current_video_index >= len(self.video_list) - 1:
                return
            self.current_video_index += 1
            self._load_video_at_index()
            return
        if not self.image_list or self.current_image_index >= len(self.image_list) - 1:
            return
        self.current_image_index += 1
        self._load_image_at_index()
    
    def _load_image_at_index(self):
        if not self.image_list or self.current_image_index >= len(self.image_list):
            return
        self.stop_detection()
        self._clear_display()
        img_path = self.image_list[self.current_image_index]
        self.current_source = ImageSource(str(img_path))
        self.statusBar().showMessage(
            f"图片: {img_path.name} ({self.current_image_index + 1}/{len(self.image_list)})")
        self._update_browse_buttons(self.current_image_index > 0, self.current_image_index < len(self.image_list) - 1)
        # 自动显示图片
        frame = self.current_source.get_frame()
        if frame is not None:
            self._display_image(frame, self.original_label)
            self.start_detection()
    
    def _load_video_at_index(self):
        if not self.video_list or self.current_video_index >= len(self.video_list):
            return
        self.stop_detection()
        self._clear_display()
        vid_path = self.video_list[self.current_video_index]
        self.current_source = VideoSource(str(vid_path))
        self.statusBar().showMessage(f"视频: {vid_path.name} ({self.current_video_index + 1}/{len(self.video_list)})")
        self._update_browse_buttons(self.current_video_index > 0, self.current_video_index < len(self.video_list) - 1)
        # 确保布局已完成，label.size() 返回正确值
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        frame = self.current_source.get_frame()
        if frame is not None:
            self._last_frame = frame
            detections, processed, edges = self.detector.detect(frame)
            result_frame = draw_detections(frame, detections)
            self._last_result = result_frame
            self._last_edges = edges
            options = self.control_panel.get_display_options()
            if options['show_original']:
                self._display_image(frame, self.original_label)
            if options['show_processed']:
                self._display_image(result_frame, self.result_label)
            if options['show_edges']:
                self._display_image(edges, self.edges_label)
            self.start_detection()
        # 更新进度条范围
        if self.video_slider is not None:
            total = self.current_source.frame_count
            if total > 0:
                self.video_slider.setMaximum(total - 1)
                self.video_slider.setValue(0)
                fps_val = self.current_source.get_fps() or 30
                self.video_current_time_label.setText(self._format_time(0))
                self.video_total_time_label.setText(self._format_time(total / fps_val))

    @pyqtSlot(str, object)
    def _on_param_changed(self, name, value):
        param_map = {
            "模糊核大小": "blur_kernel_size",
            "CLAHE限制": "clahe_clip_limit",
            "Canny低阈值": "canny_low",
            "Canny高阈值": "canny_high",
            "霍夫阈值": "hough_threshold",
            "最小长度": "min_line_length",
            "最大线段间隔": "max_line_gap",
            "角度容差": "angle_tolerance"
        }
        param_name = param_map.get(name)
        if param_name:
            if param_name == "blur_kernel_size" and value % 2 == 0:
                value += 1
                self.control_panel.set_params({"blur_kernel_size": value})
            elif param_name == "canny_low" and value >= self.detector.canny_high:
                value = max(0, self.detector.canny_high - 1)
                self.control_panel.set_params({"canny_low": value})
            elif param_name == "canny_high" and value <= self.detector.canny_low:
                value = min(255, self.detector.canny_low + 1)
                self.control_panel.set_params({"canny_high": value})
            self.detector.update_params(**{param_name: value})
            # 视频暂停时改参数，重新检测当前帧
            if isinstance(self.current_source, VideoSource) and self.is_detecting and not self.is_video_playing and self._last_frame is not None:
                detections, processed, edges = self.detector.detect(self._last_frame)
                result_frame = draw_detections(self._last_frame, detections)
                self._last_result = result_frame
                self._last_edges = edges
                options = self.control_panel.get_display_options()
                if options['show_processed']:
                    self._display_image(result_frame, self.result_label)
                if options['show_edges']:
                    self._display_image(edges, self.edges_label)
            # 图片源改参数时，重新检测当前图片并更新放大窗口
            elif isinstance(self.current_source, ImageSource) and self.is_detecting and self._last_frame is not None:
                detections, processed, edges = self.detector.detect(self._last_frame)
                result_frame = draw_detections(self._last_frame, detections)
                self._last_result = result_frame
                self._last_edges = edges
                options = self.control_panel.get_display_options()
                if options['show_processed']:
                    self._display_image(result_frame, self.result_label)
                if options['show_edges']:
                    self._display_image(edges, self.edges_label)

    @pyqtSlot()
    def _on_display_option_changed(self):
        """显示选项改变时更新面板可见性"""
        options = self.control_panel.get_display_options()
        self.original_label.setVisible(options['show_original'])
        self.result_label.setVisible(options['show_processed'])
        self.edges_label.setVisible(options['show_edges'])
        self.display_layout.invalidate()
        QTimer.singleShot(0, self._refresh_visible_cached_images)

    def _refresh_visible_cached_images(self):
        """布局尺寸更新后，按当前可见区域重新缩放缓存图像。"""
        options = self.control_panel.get_display_options()
        if options['show_original'] and self._last_frame is not None:
            self._display_image(self._last_frame, self.original_label)
        if options['show_processed'] and self._last_result is not None:
            self._display_image(self._last_result, self.result_label)
        if options['show_edges'] and self._last_edges is not None:
            self._display_image(self._last_edges, self.edges_label)

    @pyqtSlot()
    def _on_reset_params(self):
        """恢复默认参数"""
        self.control_panel.reset_to_defaults()
        # 同步更新检测器参数
        self.detector.update_params(
            blur_kernel_size=5,
            clahe_clip_limit=2.0,
            canny_low=50,
            canny_high=150,
            hough_threshold=50,
            min_line_length=50,
            max_line_gap=10,
            angle_tolerance=15
        )
        self.statusBar().showMessage("已恢复默认参数")

    def _refresh_profile_list(self):
        """刷新参数模板列表"""
        names = self.config_manager.get_profile_names()
        self.control_panel.set_profiles(names, "默认")

    @pyqtSlot(str)
    def _on_profile_changed(self, name: str):
        """切换参数模板"""
        if not name:
            return
        profile = self.config_manager.get_profile(name)
        if profile:
            self.control_panel.set_params(profile)
            self.detector.update_params(**profile)
            self.statusBar().showMessage(f"已切换到参数模板: {name}")

    @pyqtSlot()
    def _on_new_profile(self):
        """新建参数模板（复制当前参数）"""
        params = self.control_panel.get_params()
        # 生成默认名称
        base_name = "新模板"
        counter = 1
        existing_names = self.config_manager.get_profile_names()
        while f"{base_name}{counter}" in existing_names:
            counter += 1
        name = f"{base_name}{counter}"
        if self.config_manager.save_profile(name, params):
            self._refresh_profile_list()
            self.control_panel.profile_combo.setCurrentText(name)
            self.statusBar().showMessage(f"已新建参数模板: {name}")

    @pyqtSlot()
    def _on_save_profile(self):
        """保存当前参数到模板（支持重命名）"""
        name = self.control_panel.get_current_profile()
        if not name:
            return
        params = self.control_panel.get_params()
        # 检查是否是重命名（名称不在现有列表中）
        existing_names = self.config_manager.get_profile_names()
        if name not in existing_names:
            # 找到之前的模板名称并重命名
            # 这种情况是用户编辑了combo的文本
            # 我们需要找到之前选中的模板
            # 简单处理：直接保存为新模板
            pass
        if self.config_manager.save_profile(name, params):
            self._refresh_profile_list()
            self.control_panel.profile_combo.setCurrentText(name)
            self.statusBar().showMessage(f"已保存参数模板: {name}")
        else:
            QMessageBox.critical(self, "错误", "保存参数模板失败")

    @pyqtSlot()
    def _on_delete_profile(self):
        """删除当前选中的参数模板"""
        name = self.control_panel.get_current_profile()
        if not name:
            return
        # 检查是否是最后一个模板
        if len(self.config_manager.get_profile_names()) <= 1:
            QMessageBox.warning(self, "警告", "不能删除最后一个参数模板")
            return
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除参数模板「{name}」吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.config_manager.delete_profile(name):
                self._refresh_profile_list()
                self.statusBar().showMessage(f"已删除参数模板: {name}")
            else:
                QMessageBox.critical(self, "错误", "删除参数模板失败")
    
    @pyqtSlot()
    def _on_file_select(self):
        current_source = self.control_panel.source_combo.currentText()
        if current_source == "视频文件":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择视频文件", "",
                "视频文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*)")
            if file_path:
                self.current_source = VideoSource(file_path)
                # 显示视频第一帧作为预览
                frame = self.current_source.get_frame()
                if frame is not None:
                    self._display_image(frame, self.original_label)
                self.statusBar().showMessage(f"已加载视频: {file_path}")
                # 更新进度条范围
                if self.video_slider is not None:
                    total = self.current_source.frame_count
                    if total > 0:
                        self.video_slider.setMaximum(total - 1)
                        self.video_slider.setValue(0)
                        fps_val = self.current_source.get_fps() or 30
                        self.video_current_time_label.setText(self._format_time(0))
                        self.video_total_time_label.setText(self._format_time(total / fps_val))
        elif current_source == "图像文件":
            default_dir = str(app_path("data", "images"))
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择图像文件", default_dir,
                "图像文件 (*.jpg *.jpeg *.png *.bmp);;所有文件 (*)")
            if file_path:
                self.stop_detection()
                self._clear_display()
                self.current_source = ImageSource(file_path)
                # 加载同目录下的所有图片以支持浏览
                file_path_obj = Path(file_path)
                self.image_list = ImageSource.list_images(file_path_obj.parent)
                self.current_image_index = 0
                # 找到选中文件在列表中的位置
                for idx, img_path in enumerate(self.image_list):
                    if img_path.resolve() == file_path_obj.resolve():
                        self.current_image_index = idx
                        break
                self._update_browse_buttons(
                    self.current_image_index > 0,
                    self.current_image_index < len(self.image_list) - 1)
                self.statusBar().showMessage(f"已加载图像: {file_path}")
                # 自动显示图片
                frame = self.current_source.get_frame()
                if frame is not None:
                    self._display_image(frame, self.original_label)
                    self.start_detection()

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
        self.preview_timer.stop()
        # 如果视频已播放完毕，从头开始
        if isinstance(self.current_source, VideoSource):
            if self.current_source.current_frame >= self.current_source.frame_count:
                self.current_source.seek(0)
        self.is_detecting = True
        self.control_panel.detect_button.setText("停止检测")
        self.statusBar().showMessage("检测中...")
        # 视频源：只标记检测开启，不启动播放定时器
        if isinstance(self.current_source, VideoSource):
            if self.video_play_btn is not None:
                self.video_play_btn.setText("⏸" if self.is_video_playing else "▶")
            if self.is_video_playing:
                fps = self.current_source.get_fps() or 30
                self.timer.start(int(1000 / fps))
        else:
            fps = 30
            if isinstance(self.current_source, ImageSource):
                fps = 5
            self.timer.start(int(1000 / fps))
        # 视频源：配置进度条范围
        if isinstance(self.current_source, VideoSource) and self.video_slider is not None:
            total = self.current_source.frame_count
            if total > 0:
                self.video_slider.setMaximum(total - 1)
                self.video_slider.setValue(self.current_source.current_frame)
                fps_val = self.current_source.get_fps() or 30
                self.video_current_time_label.setText(self._format_time(self.current_source.current_frame / fps_val))
                self.video_total_time_label.setText(self._format_time(total / fps_val))
        if self.video_play_btn is not None:
            self.video_play_btn.setText("⏸")

    def stop_detection(self):
        self.is_detecting = False
        self.control_panel.detect_button.setText("开始检测")
        self.statusBar().showMessage("已停止")
        self._stop_video_recording()
        # 视频源：不停止播放定时器，由 is_video_playing 控制
        if isinstance(self.current_source, VideoSource):
            if not self.is_video_playing:
                self.timer.stop()
        else:
            self.timer.stop()
        # 如果是摄像头源，恢复预览
        if isinstance(self.current_source, CameraSource):
            self.preview_timer.start(33)
        if self.video_play_btn is not None and not isinstance(self.current_source, VideoSource):
            self.video_play_btn.setText("▶")

    def _process_frame(self):
        if not self.is_detecting or self.current_source is None:
            return
        frame = self.current_source.get_frame()
        if frame is None:
            # 视频播放完毕：回到第0帧并暂停，不退出检测
            if isinstance(self.current_source, VideoSource):
                self.is_video_playing = False
                self.timer.stop()
                self.current_source.seek(0)
                if self.video_play_btn is not None:
                    self.video_play_btn.setText("▶")
                self._update_video_progress()
                # 检测并显示第0帧
                frame0 = self.current_source.get_frame()
                if frame0 is not None:
                    self._last_frame = frame0
                    det, proc, edg = self.detector.detect(frame0)
                    res = draw_detections(frame0, det)
                    self._last_result = res
                    self._last_edges = edg
                    opts = self.control_panel.get_display_options()
                    if opts['show_original']:
                        self._display_image(frame0, self.original_label)
                    if opts['show_processed']:
                        self._display_image(res, self.result_label)
                    if opts['show_edges']:
                        self._display_image(edg, self.edges_label)
                self.statusBar().showMessage("视频播放完毕，已回到起点")
            else:
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
        if self._auto_save:
            self._save_frame(frame, result_frame, edges)
        if isinstance(self.current_source, VideoSource):
            self._update_video_progress()
        self.statusBar().showMessage(f"检测到 {len(detections)} 条焊缝")

    def _detect_current_image_once(self):
        """对静态图片执行一次检测并更新结果视图"""
        if not isinstance(self.current_source, ImageSource):
            return
        frame = self.current_source.get_frame()
        if frame is None:
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
        # 自动保存引用以便放大查看
        if label is self.original_label:
            self._last_frame = image
        elif label is self.result_label:
            self._last_result = image
        elif label is self.edges_label:
            self._last_edges = image
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
        label.set_image_pixmap(pixmap)

    # ---------- 视频进度条（动态创建/销毁） ----------

    @staticmethod
    def _format_time(seconds: float) -> str:
        seconds = max(0, int(seconds))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def _build_time_label(self, sample_text: str) -> QLabel:
        label = QLabel(sample_text)
        label.setAlignment(Qt.AlignCenter)
        label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        label.setMinimumWidth(label.fontMetrics().horizontalAdvance(sample_text) + 16)
        return label

    def _create_video_progress(self):
        """在 display_layout 末尾动态创建视频进度条"""
        if self.video_progress_row is not None:
            return
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 2, 0, 0)
        self.video_current_time_label = self._build_time_label("00:00")
        self.video_slider = ClickableSlider(Qt.Horizontal)
        self.video_slider.setFocusPolicy(Qt.NoFocus)
        self.video_slider.setMinimum(0)
        self.video_slider.setMaximum(0)
        self.video_total_time_label = self._build_time_label("00:00")
        # 播放/暂停按钮
        self.video_play_btn = QPushButton("▶")
        self.video_play_btn.setFixedWidth(36)
        self.video_play_btn.setFocusPolicy(Qt.NoFocus)
        self.video_play_btn.clicked.connect(self._toggle_video_detect)
        lay.addWidget(self.video_play_btn)
        lay.addWidget(self.video_current_time_label)
        lay.addWidget(self.video_slider, 1)
        lay.addWidget(self.video_total_time_label)
        self.video_slider.sliderPressed.connect(self._on_video_slider_pressed)
        self.video_slider.sliderReleased.connect(self._on_video_slider_released)
        self.video_slider.valueChanged.connect(self._on_video_slider_moved)
        # 添加到 display_layout（图片标签之后、control_panel 之前）
        self.display_layout.addWidget(row)
        self.video_progress_row = row

    def _destroy_video_progress(self):
        """销毁视频进度条控件"""
        if self.video_progress_row is None:
            return
        self._progress_dragging = False
        self.video_slider.blockSignals(True)
        self.display_layout.removeWidget(self.video_progress_row)
        self.video_progress_row.deleteLater()
        self.video_progress_row = None
        self.video_slider = None
        self.video_current_time_label = None
        self.video_total_time_label = None
        self.video_play_btn = None

    def _toggle_space_action(self):
        """空格键：视频源切换播放，其他源切换检测"""
        if isinstance(self.current_source, VideoSource) and self.video_play_btn is not None:
            self._toggle_video_detect()
        else:
            self._on_detect_clicked()

    def _toggle_video_detect(self):
        """切换视频播放/暂停（检测始终开启）"""
        if self.is_video_playing:
            self.is_video_playing = False
            self.timer.stop()
            if self.video_play_btn is not None:
                self.video_play_btn.setText("▶")
        else:
            self.is_video_playing = True
            fps = self.current_source.get_fps() or 30
            self.timer.start(int(1000 / fps))
            if self.video_play_btn is not None:
                self.video_play_btn.setText("⏸")
    def _update_video_progress(self):
        if self.video_slider is None or self._progress_dragging:
            return
        if not isinstance(self.current_source, VideoSource):
            return
        current = self.current_source.current_frame
        total = self.current_source.frame_count
        if total <= 0:
            return
        self.video_slider.blockSignals(True)
        self.video_slider.setValue(current)
        self.video_slider.blockSignals(False)
        self.video_current_time_label.setText(self._format_time(current / self.current_source.get_fps()))

    def _on_video_slider_pressed(self):
        self._progress_dragging = True
        self.timer.stop()

    def _on_video_slider_released(self):
        if not isinstance(self.current_source, VideoSource):
            self._progress_dragging = False
            return
        target = self.video_slider.value()
        self._stop_video_recording()
        self.current_source.seek(target)
        self._progress_dragging = False
        if self.is_video_playing:
            fps = self.current_source.get_fps() or 30
            self.timer.start(int(1000 / fps))
        else:
            # 静止状态下跳转后检测并显示目标帧
            frame = self.current_source.get_frame()
            if frame is not None:
                self._last_frame = frame
                detections, processed, edges = self.detector.detect(frame)
                result_frame = draw_detections(frame, detections)
                self._last_result = result_frame
                self._last_edges = edges
                options = self.control_panel.get_display_options()
                if options['show_original']:
                    self._display_image(frame, self.original_label)
                if options['show_processed']:
                    self._display_image(result_frame, self.result_label)
                if options['show_edges']:
                    self._display_image(edges, self.edges_label)

    def _on_video_slider_moved(self, value: int):
        if not self._progress_dragging or self.video_slider is None:
            return
        if not isinstance(self.current_source, VideoSource):
            return
        fps = self.current_source.get_fps() or 30
        self.video_current_time_label.setText(self._format_time(value / fps))

    def _show_enlarged(self, image_type: str):
        """点击图片后放大显示"""
        from ..input_sources import VideoSource, CameraSource
        
        def _numpy_to_pixmap(img):
            """将OpenCV图像转换为QPixmap"""
            if len(img.shape) == 2:
                h, w = img.shape
                q_img = QImage(img.data, w, h, w, QImage.Format_Grayscale8)
            else:
                h, w, ch = img.shape
                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                q_img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
            return QPixmap.fromImage(q_img)
        
        # 获取对应的图像
        image = None
        title = ""
        if image_type == "original":
            image = self._last_frame
            title = "原始图像"
        elif image_type == "result":
            image = self._last_result
            title = "检测结果"
        elif image_type == "edges":
            image = self._last_edges
            title = "边缘图"

        if image is None:
            return

        # 创建放大窗口
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumSize(1200, 900)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowMaximizeButtonHint)
        dialog.setStyleSheet("QDialog { border: 3px solid #666; }")
        
        # 创建图像标签
        image_label = ScalableImageLabel()
        
        # 转换图像并显示
        image_label.setPixmap(_numpy_to_pixmap(image))
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(image_label, 1)

        # 视频源：在放大窗口底部添加进度条
        dlg_slider = None
        dlg_time_label = None
        dlg_play_btn = None
        if isinstance(self.current_source, VideoSource) and self.current_source.frame_count > 0:
            progress_row = QWidget()
            pl = QHBoxLayout(progress_row)
            pl.setContentsMargins(0, 2, 0, 0)
            # 播放/暂停按钮
            dlg_play_btn = QPushButton("⏸" if self.is_detecting else "▶")
            dlg_play_btn.setFixedWidth(36)
            dlg_play_btn.setFocusPolicy(Qt.NoFocus)
            dlg_time_label = self._build_time_label(
                "00:00 / " + self._format_time(
                    self.current_source.frame_count / (self.current_source.get_fps() or 30)
                )
            )
            dlg_slider = ClickableSlider(Qt.Horizontal)
            dlg_slider.setFocusPolicy(Qt.NoFocus)
            dlg_slider.setMinimum(0)
            dlg_slider.setMaximum(self.current_source.frame_count - 1)
            dlg_slider.setValue(self.current_source.current_frame)
            pl.addWidget(dlg_play_btn)
            pl.addWidget(dlg_time_label)
            pl.addWidget(dlg_slider, 1)
            layout.addWidget(progress_row)

            # 播放/暂停按钮逻辑（切换视频播放，不影响检测）
            def _toggle_play():
                self._toggle_video_detect()
                dlg_play_btn.setText("⏸" if self.is_video_playing else "▶")
            dlg_play_btn.clicked.connect(_toggle_play)
            # 空格键切换视频播放
            QShortcut(Qt.Key_Space, dialog).activated.connect(_toggle_play)

            # 拖拽放大窗口进度条时跳转视频
            _dlg_dragging = [False]
            def _on_dlg_pressed():
                _dlg_dragging[0] = True
                self._on_video_slider_pressed()  # 暂停主窗口播放
            def _on_dlg_released():
                _dlg_dragging[0] = False
                target = dlg_slider.value()
                self._stop_video_recording()
                self.current_source.seek(target)
                self._progress_dragging = False
                if self.is_video_playing:
                    fps_val = self.current_source.get_fps() or 30
                    self.timer.start(int(1000 / fps_val))
                else:
                    # 暂停状态下跳转后检测并更新帧
                    frame = self.current_source.get_frame()
                    if frame is not None:
                        self._last_frame = frame
                        detections, processed, edges = self.detector.detect(frame)
                        result_frame = draw_detections(frame, detections)
                        self._last_result = result_frame
                        self._last_edges = edges
            def _on_dlg_moved(val):
                if _dlg_dragging[0]:
                    fps_val = self.current_source.get_fps() or 30
                    dlg_time_label.setText(f"{self._format_time(val / fps_val)} / {self._format_time(self.current_source.frame_count / fps_val)}")
            dlg_slider.sliderPressed.connect(_on_dlg_pressed)
            dlg_slider.sliderReleased.connect(_on_dlg_released)
            dlg_slider.valueChanged.connect(_on_dlg_moved)

        # 实时更新：放大画面 + 进度条
        if isinstance(self.current_source, (VideoSource, CameraSource, ImageSource)):
            def _live_update():
                # 源已切换时停止更新
                if not isinstance(self.current_source, (VideoSource, CameraSource, ImageSource)):
                    return
                frame = None
                if image_type == "original":
                    frame = self._last_frame
                elif image_type == "result":
                    frame = self._last_result
                elif image_type == "edges":
                    frame = self._last_edges
                if frame is not None:
                    image_label.setPixmap(_numpy_to_pixmap(frame), preserve_view=True)
                # 同步进度条和按钮状态
                if dlg_play_btn is not None:
                    dlg_play_btn.setText("⏸" if self.is_video_playing else "▶")
                if dlg_slider is not None and not _dlg_dragging[0]:
                    dlg_slider.blockSignals(True)
                    dlg_slider.setValue(self.current_source.current_frame)
                    dlg_slider.blockSignals(False)
                    fps_val = self.current_source.get_fps() or 30
                    dlg_time_label.setText(f"{self._format_time(self.current_source.current_frame / fps_val)} / {self._format_time(self.current_source.frame_count / fps_val)}")

            fps = 30
            if isinstance(self.current_source, VideoSource):
                fps = self.current_source.get_fps() or 30
            live_timer = QTimer(dialog)
            live_timer.timeout.connect(_live_update)
            live_timer.start(int(1000 / fps))
            self._enlarged_live_timer = live_timer

        # 关闭之前的放大窗口
        if self._enlarged_dialog is not None:
            self._enlarged_dialog.close()
        self._enlarged_dialog = dialog
        dialog.show()
    
    def closeEvent(self, event):
        self.stop_detection()
        self.preview_timer.stop()
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
        self.preview_timer.stop()
        # 拖放切换源前关闭放大窗口
        if getattr(self, "_enlarged_live_timer", None) is not None:
            self._enlarged_live_timer.stop()
            self._enlarged_live_timer = None
        if self._enlarged_dialog is not None:
            self._enlarged_dialog.close()
            self._enlarged_dialog = None
        for url in event.mimeData().urls():
            file_path = Path(url.toLocalFile())
            if not file_path.exists():
                continue
            suffix = file_path.suffix.lower()
            if suffix in self._SUPPORTED_IMAGE:
                self.stop_detection()
                self._clear_display()
                self.current_source = ImageSource(str(file_path))
                self.image_list = ImageSource.list_images(file_path.parent)
                self.current_image_index = 0
                for idx, img_path in enumerate(self.image_list):
                    if img_path.resolve() == file_path.resolve():
                        self.current_image_index = idx
                        break
                self._update_browse_buttons(
                    self.current_image_index > 0,
                    self.current_image_index < len(self.image_list) - 1)
                self._display_image(self.current_source.get_frame(), self.original_label)
                self.start_detection()
                # 用 blockSignals 防止 setCurrentText 触发 _on_source_changed
                self.control_panel.source_combo.blockSignals(True)
                self.control_panel.source_combo.setCurrentText("图像文件")
                self.control_panel.source_combo.blockSignals(False)
                self.statusBar().showMessage(f"已拖入图像: {file_path.name}")
                event.acceptProposedAction()
                return
            if suffix in self._SUPPORTED_VIDEO:
                self.stop_detection()
                self.current_source = VideoSource(str(file_path))
                # 显示视频第一帧作为预览
                frame = self.current_source.get_frame()
                if frame is not None:
                    self._display_image(frame, self.original_label)
                self.control_panel.source_combo.blockSignals(True)
                self.control_panel.source_combo.setCurrentText("视频文件")
                self.control_panel.source_combo.blockSignals(False)
                self.statusBar().showMessage(f"已拖入视频: {file_path.name}")
                event.acceptProposedAction()
                return
        event.ignore()

    def _save_frame(self, original, result, edges):
        # 视频/摄像头源：写入视频文件
        if isinstance(self.current_source, (VideoSource, CameraSource)):
            if self._vw_original is None:
                self._start_video_recording(original)
            if self._vw_original is not None:
                self._vw_original.write(original)
                self._vw_result.write(result)
                self._vw_edges.write(edges)
        else:
            # 图片源：保存为 PNG
            self._save_detection_images(original, result, edges)

    def _start_video_recording(self, frame):
        now = datetime.datetime.now()
        base_dir = app_path("data", "saved")
        self._save_session_dir = base_dir / now.strftime("%Y-%m-%d") / now.strftime("%H-%M-%S_%f")
        self._save_session_dir.mkdir(parents=True, exist_ok=True)

        h, w = frame.shape[:2]
        fps = 30
        if isinstance(self.current_source, VideoSource):
            fps = self.current_source.get_fps() or 30

        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        self._vw_original = cv2.VideoWriter(str(self._save_session_dir / "original.avi"), fourcc, fps, (w, h))
        self._vw_result = cv2.VideoWriter(str(self._save_session_dir / "result.avi"), fourcc, fps, (w, h))
        self._vw_edges = cv2.VideoWriter(str(self._save_session_dir / "edges.avi"), fourcc, fps, (w, h), isColor=False)
        self.statusBar().showMessage(f"检测中，已开始录像: {self._save_session_dir.name}")

    def _stop_video_recording(self):
        for vw_name in ("_vw_original", "_vw_result", "_vw_edges"):
            vw = getattr(self, vw_name, None)
            if vw is not None:
                vw.release()
                setattr(self, vw_name, None)
        if self._save_session_dir is not None:
            self._save_session_dir = None

    def _save_detection_images(self, original, result, edges):
        """保存检测图像到 data/saved/"""
        now = datetime.datetime.now()
        base_dir = app_path("data", "saved")
        session_dir = base_dir / now.strftime("%Y-%m-%d") / now.strftime("%H-%M-%S")
        session_dir.mkdir(parents=True, exist_ok=True)
        ts = now.strftime("%H%M%S%f")
        cv2.imwrite(str(session_dir / f"image_original_{ts}.png"), original)
        cv2.imwrite(str(session_dir / f"image_result_{ts}.png"), result)
        cv2.imwrite(str(session_dir / f"image_edges_{ts}.png"), edges)

    def _clear_display(self):
        """清除残留的检测结果图像"""
        self.result_label.clear()
        self.edges_label.clear()
        self._last_result = None
        self._last_edges = None
    
