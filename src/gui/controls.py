"""
GUI控制组件模块

提供参数调整的控件。
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QSlider, QSpinBox, QDoubleSpinBox,
    QComboBox, QPushButton, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from typing import Dict, Any


class ControlPanel(QWidget):
    """控制面板
    
    提供检测参数的调整控件。
    
    Signals:
        param_changed: 参数改变信号 (param_name, value)
        detect_clicked: 检测按钮点击信号
        source_changed: 输入源改变信号
    """
    
    param_changed = pyqtSignal(str, object)
    detect_clicked = pyqtSignal()
    source_changed = pyqtSignal(str)
    prev_image_clicked = pyqtSignal()
    next_image_clicked = pyqtSignal()
    display_option_changed = pyqtSignal()
    reset_params_clicked = pyqtSignal()
    profile_changed = pyqtSignal(str)      # 参数模板切换
    new_profile_clicked = pyqtSignal()      # 新建参数模板
    save_profile_clicked = pyqtSignal()    # 保存参数模板
    delete_profile_clicked = pyqtSignal()  # 删除参数模板
    
    def __init__(self, parent=None):
        """初始化控制面板"""
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 输入源选择
        source_group = QGroupBox("输入源")
        source_layout = QVBoxLayout()
        
        self.source_combo = QComboBox()
        self.source_combo.addItems(["摄像头", "视频文件", "图像文件"])
        self.source_combo.currentTextChanged.connect(self._on_source_changed)
        
        self.file_button = QPushButton("选择文件")
        self.file_button.setEnabled(False)
        
        # 图片浏览按钮
        self.prev_button = QPushButton("上一张")
        self.prev_button.setEnabled(False)
        self.prev_button.clicked.connect(self.prev_image_clicked.emit)
        self.next_button = QPushButton("下一张")
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self.next_image_clicked.emit)
        
        source_layout.addWidget(self.source_combo)
        source_layout.addWidget(self.file_button)
        
        browse_layout = QHBoxLayout()
        browse_layout.addWidget(self.prev_button)
        browse_layout.addWidget(self.next_button)
        source_layout.addLayout(browse_layout)
        
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)
        
        # 预处理参数
        preproc_group = QGroupBox("预处理参数")
        preproc_layout = QVBoxLayout()
        
        self.blur_slider = self._create_slider(
            "模糊核大小", 1, 31, 5, 2
        )
        self.clahe_slider = self._create_double_slider(
            "CLAHE限制", 0.1, 10.0, 2.0, 0.1
        )
        
        preproc_layout.addWidget(self.blur_slider)
        preproc_layout.addWidget(self.clahe_slider)
        preproc_group.setLayout(preproc_layout)
        layout.addWidget(preproc_group)

        # 检测参数
        detect_group = QGroupBox("检测参数")
        detect_layout = QVBoxLayout()

        # 参数模板（嵌入检测参数顶部）
        profile_layout = QHBoxLayout()
        profile_layout.setSpacing(6)
        self.profile_combo = QComboBox()
        self.profile_combo.setEditable(True)
        self.profile_combo.currentTextChanged.connect(self.profile_changed.emit)
        self.new_profile_button = QPushButton("新建")
        self.new_profile_button.clicked.connect(self.new_profile_clicked.emit)
        self.save_profile_button = QPushButton("保存")
        self.save_profile_button.clicked.connect(self.save_profile_clicked.emit)
        self.delete_profile_button = QPushButton("删除")
        self.delete_profile_button.clicked.connect(self.delete_profile_clicked.emit)
        self.new_profile_button.setFixedWidth(55)
        self.save_profile_button.setFixedWidth(55)
        self.delete_profile_button.setFixedWidth(55)
        right_layout = QHBoxLayout()
        right_layout.setSpacing(4)
        right_layout.addWidget(self.new_profile_button)
        right_layout.addWidget(self.save_profile_button)
        right_layout.addWidget(self.delete_profile_button)
        profile_layout.addWidget(QLabel("模板:"))
        profile_layout.addWidget(self.profile_combo, 1)
        profile_layout.addLayout(right_layout)
        detect_layout.addLayout(profile_layout)

        self.canny_low_slider = self._create_slider(
            "Canny低阈值", 0, 255, 50, 5
        )
        self.canny_high_slider = self._create_slider(
            "Canny高阈值", 0, 255, 150, 5
        )
        self.hough_slider = self._create_slider(
            "霍夫阈值", 1, 200, 50, 5
        )
        self.min_length_slider = self._create_slider(
            "最小长度", 10, 500, 50, 10
        )
        self.max_gap_slider = self._create_slider(
            "最大线段间隔", 1, 100, 10, 1
        )
        self.angle_tolerance_slider = self._create_slider(
            "角度容差", 1, 90, 15, 1
        )
        
        detect_layout.addWidget(self.canny_low_slider)
        detect_layout.addWidget(self.canny_high_slider)
        detect_layout.addWidget(self.hough_slider)
        detect_layout.addWidget(self.min_length_slider)
        detect_layout.addWidget(self.max_gap_slider)
        detect_layout.addWidget(self.angle_tolerance_slider)
        detect_group.setLayout(detect_layout)
        layout.addWidget(detect_group)
        
        # 显示选项
        display_group = QGroupBox("显示选项")
        display_layout = QVBoxLayout()
        
        self.show_original_check = QCheckBox("显示原图")
        self.show_original_check.setChecked(True)
        self.show_processed_check = QCheckBox("显示处理图")
        self.show_processed_check.setChecked(True)
        self.show_edges_check = QCheckBox("显示边缘图")
        self.show_edges_check.setChecked(False)
        
        display_layout.addWidget(self.show_original_check)
        display_layout.addWidget(self.show_processed_check)
        display_layout.addWidget(self.show_edges_check)
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        
        self.show_original_check.stateChanged.connect(lambda: self.display_option_changed.emit())
        self.show_processed_check.stateChanged.connect(lambda: self.display_option_changed.emit())
        self.show_edges_check.stateChanged.connect(lambda: self.display_option_changed.emit())
        
        # 检测按钮
        self.detect_button = QPushButton("开始检测")
        self.detect_button.clicked.connect(self.detect_clicked.emit)
        layout.addWidget(self.detect_button)

        # 恢复默认参数按钮
        self.reset_button = QPushButton("恢复默认参数")
        self.reset_button.clicked.connect(self.reset_params_clicked.emit)
        layout.addWidget(self.reset_button)
        
        layout.addStretch()
    
    def _create_slider(
        self,
        label: str,
        min_val: int,
        max_val: int,
        default: int,
        step: int = 1
    ) -> QWidget:
        """创建滑块控件"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        label_widget = QLabel(label)
        label_widget.setFixedWidth(100)
        
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default)
        slider.setSingleStep(step)
        
        spin = QSpinBox()
        spin.setMinimum(min_val)
        spin.setMaximum(max_val)
        spin.setValue(default)
        spin.setFixedWidth(60)
        
        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        slider.valueChanged.connect(
            lambda v, name=label: self.param_changed.emit(name, v)
        )
        
        layout.addWidget(label_widget)
        layout.addWidget(slider)
        layout.addWidget(spin)
        
        return widget
    
    def _create_double_slider(
        self,
        label: str,
        min_val: float,
        max_val: float,
        default: float,
        step: float = 0.1
    ) -> QWidget:
        """创建浮点数滑块控件"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        label_widget = QLabel(label)
        label_widget.setFixedWidth(100)
        
        spin = QDoubleSpinBox()
        spin.setMinimum(min_val)
        spin.setMaximum(max_val)
        spin.setValue(default)
        spin.setSingleStep(step)
        spin.setFixedWidth(80)
        
        spin.valueChanged.connect(
            lambda v, name=label: self.param_changed.emit(name, v)
        )
        
        layout.addWidget(label_widget)
        layout.addWidget(spin)
        layout.addStretch()
        
        return widget
    
    def _on_source_changed(self, text: str):
        """输入源改变处理"""
        source_map = {
            "摄像头": "camera",
            "视频文件": "video",
            "图像文件": "image"
        }
        source = source_map.get(text, "camera")
        self.file_button.setEnabled(source != "camera")
        self.source_changed.emit(source)
    
    def get_params(self) -> Dict[str, Any]:
        """获取当前参数"""
        return {
            'blur_kernel_size': self.blur_slider.findChild(QSlider).value(),
            'canny_low': self.canny_low_slider.findChild(QSlider).value(),
            'canny_high': self.canny_high_slider.findChild(QSlider).value(),
            'hough_threshold': self.hough_slider.findChild(QSlider).value(),
            'min_line_length': self.min_length_slider.findChild(QSlider).value(),
            'max_line_gap': self.max_gap_slider.findChild(QSlider).value(),
            'angle_tolerance': self.angle_tolerance_slider.findChild(QSlider).value(),
        }
    
    def set_params(self, params: Dict[str, Any]):
        """设置参数"""
        if 'blur_kernel_size' in params:
            self.blur_slider.findChild(QSlider).setValue(int(params['blur_kernel_size']))
        if 'canny_low' in params:
            self.canny_low_slider.findChild(QSlider).setValue(int(params['canny_low']))
        if 'canny_high' in params:
            self.canny_high_slider.findChild(QSlider).setValue(int(params['canny_high']))
        if 'hough_threshold' in params:
            self.hough_slider.findChild(QSlider).setValue(int(params['hough_threshold']))
        if 'min_line_length' in params:
            self.min_length_slider.findChild(QSlider).setValue(int(params['min_line_length']))
        if 'max_line_gap' in params:
            self.max_gap_slider.findChild(QSlider).setValue(int(params['max_line_gap']))
        if 'angle_tolerance' in params:
            self.angle_tolerance_slider.findChild(QSlider).setValue(int(params['angle_tolerance']))

    def reset_to_defaults(self):
        """重置所有参数为默认值"""
        defaults = {
            'blur_kernel_size': 5,
            'canny_low': 50,
            'canny_high': 150,
            'hough_threshold': 50,
            'min_line_length': 50,
            'max_line_gap': 10,
            'angle_tolerance': 15,
        }
        self.set_params(defaults)
    
    def get_display_options(self) -> Dict[str, bool]:
        """获取显示选项状态"""
        return {
            'show_original': self.show_original_check.isChecked(),
            'show_processed': self.show_processed_check.isChecked(),
            'show_edges': self.show_edges_check.isChecked(),
        }

    def set_profiles(self, names: list, current: str = None):
        """设置参数模板列表
        
        Args:
            names: 模板名称列表
            current: 当前选中的模板名称
        """
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(names)
        if current and current in names:
            self.profile_combo.setCurrentText(current)
        self.profile_combo.blockSignals(False)

    def get_current_profile(self) -> str:
        """获取当前选中的参数模板名称"""
        return self.profile_combo.currentText()
