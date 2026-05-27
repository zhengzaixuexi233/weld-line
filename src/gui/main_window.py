"""
GUI主窗口模块
"""
import cv2
import numpy as np
from pathlib import Path
import datetime
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFileDialog, QStatusBar, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QPointF, QSizeF, QRectF
from PyQt5.QtGui import QImage, QPixmap, QDragEnterEvent, QDropEvent, QCursor, QPainter
from typing import Optional

from .controls import ControlPanel
from ..core.detector import WeldDetector
from ..input_sources import ImageSource, VideoSource, CameraSource
from ..config.manager import ConfigManager
from ..utils.visualization import draw_detections

from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import pyqtSignal

class ClickableLabel(QLabel):
    """可点击的QLabel，点击后发射clicked信号"""
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


class ScalableImageLabel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_pixmap = None
        self._zoom_factor = 1.0
        self._dragging = False
        self._last_drag_pos = None
        self._offset = QPointF(0, 0)
        self.setCursor(QCursor(Qt.OpenHandCursor))

    def setPixmap(self, pixmap):
        self._original_pixmap = pixmap
        self._zoom_factor = 1.0
        self._offset = QPointF(0, 0)
        self.update()

    def wheelEvent(self, event):
        if self._original_pixmap is None:
            return
        delta = event.angleDelta().y()
        if delta > 0:
            self._zoom_factor += 0.2
        elif delta < 0:
            self._zoom_factor -= 0.2
        self._zoom_factor = max(0.8, min(3.0, self._zoom_factor))
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
        self.image_list = []
        self.current_image_index = 0
        self._last_frame = None
        self._last_result = None
        self._last_edges = None
        self._auto_save = False
        self._vw_original = None
        self._vw_result = None
        self._vw_edges = None
        self._save_session_dir = None
        self._is_drop_action = False  # 标记是否正在执行拖放操作
        self.setAcceptDrops(True)
        self._init_ui()
        self._load_config()
        self._setup_timer()
        # 默认初始化摄像头源
        self._on_source_changed("camera")
    
    def _init_ui(self):
        self.setWindowTitle("焊缝识别系统")
        self.setMinimumSize(1200, 800)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        display_layout = QVBoxLayout()
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
        self.control_panel.setFixedWidth(380)
        
        self.control_panel.detect_clicked.connect(self._on_detect_clicked)
        self.control_panel.source_changed.connect(self._on_source_changed)
        self.control_panel.param_changed.connect(self._on_param_changed)
        self.control_panel.file_button.clicked.connect(self._on_file_select)
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
        
        main_layout.addLayout(display_layout)
        main_layout.addWidget(self.control_panel)
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
        saved_dir = Path(__file__).resolve().parents[2] / "data" / "saved"
        saved_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(saved_dir))


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
        self.stop_detection()
        self._clear_display()
        self.preview_timer.stop()
        if source == "camera":
            self.current_source = CameraSource()
            # 打开摄像头并开始预览
            if self.current_source.open():
                self.preview_timer.start(33)  # ~30fps 预览
                self.statusBar().showMessage("摄像头已打开，点击「开始检测」进行焊缝检测")
            else:
                self.statusBar().showMessage("无法打开摄像头")
        elif source == "image":
            # 自动扫描 data/images 目录
            images_dir = Path(__file__).resolve().parents[2] / "data" / "images"
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
        elif current_source == "图像文件":
            default_dir = str(Path(__file__).resolve().parents[2] / "data" / "images")
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
        fps = 30
        if isinstance(self.current_source, VideoSource):
            fps = self.current_source.get_fps()
        elif isinstance(self.current_source, ImageSource):
            fps = 5
        self.timer.start(int(1000 / fps))
    
    def stop_detection(self):
        self.is_detecting = False
        self.timer.stop()
        self.control_panel.detect_button.setText("开始检测")
        self.statusBar().showMessage("已停止")
        self._stop_video_recording()
        # 如果是摄像头源，恢复预览
        if isinstance(self.current_source, CameraSource):
            self.preview_timer.start(33)
    
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
        if self._auto_save:
            self._save_frame(frame, result_frame, edges)
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
        
        # 视频/摄像头源：实时更新放大画面
        if isinstance(self.current_source, (VideoSource, CameraSource)):
            def _live_update():
                frame = None
                if image_type == "original":
                    frame = self._last_frame
                elif image_type == "result":
                    frame = self._last_result
                elif image_type == "edges":
                    frame = self._last_edges
                if frame is not None:
                    image_label.setPixmap(_numpy_to_pixmap(frame))
            
            fps = 30
            if isinstance(self.current_source, VideoSource):
                fps = self.current_source.get_fps() or 30
            live_timer = QTimer(dialog)
            live_timer.timeout.connect(_live_update)
            live_timer.start(int(1000 / fps))

        # 布局
        layout = QVBoxLayout(dialog)
        layout.addWidget(image_label)

        dialog.exec_()
    
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
        base_dir = Path(__file__).resolve().parents[2] / "data" / "saved"
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
        base_dir = Path(__file__).resolve().parents[2] / "data" / "saved"
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
    
