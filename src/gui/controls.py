"""
GUI控制组件模块

提供参数调整的控件。
"""

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QSlider,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QPushButton,
    QCheckBox,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QEvent
from typing import Dict, Any

# 参数提示信息字典
PARAM_TOOLTIPS = {
    "模糊核大小": (
        "【作用】控制高斯模糊的降噪强度，是图像预处理的第一步。\n"
        "  降噪可以减少图像中的随机噪声，避免后续边缘检测产生大量误检。\n"
        "\n"
        "【原理】使用高斯核对图像进行卷积运算，每个像素被替换为\n"
        "  周围像素的加权平均值。核大小决定了参与平均的像素范围：\n"
        "  核越大，平均范围越广，模糊效果越强，但会丢失细节。\n"
        "  例如：核大小为5时，每个像素参考周围5×5区域的信息。\n"
        "\n"
        "【建议】\n"
        "  • 噪声多的图像：增大到 7-11\n"
        "  • 清晰图像：保持 3-5\n"
        "  • 值过大会模糊焊缝细节"
    ),
    "CLAHE限制": (
        "【作用】控制自适应直方图均衡化（CLAHE）的对比度增强强度。\n"
        "  对比度增强可以使焊缝边缘更加清晰，便于后续检测。\n"
        "\n"
        "【原理】CLAHE将图像分成小块（网格），对每块独立进行直方图\n"
        "  均衡化。clipLimit参数限制了直方图的裁剪高度：\n"
        "  - 当某灰度级的像素数超过clipLimit时，超出部分会被均匀\n"
        "    分配到其他灰度级\n"
        "  - 这样既增强了局部对比度，又避免了噪声被过度放大\n"
        "  - 全局直方图均衡化会导致整体过亮/过暗，CLAHE解决了这个问题\n"
        "\n"
        "【建议】\n"
        "  • 光线不均匀：增大到 3.0-4.0\n"
        "  • 正常光照：保持 1.5-2.5\n"
        "  • 值过大会放大噪声"
    ),
    "Canny低阈值": (
        "【作用】Canny边缘检测的低阈值，用于过滤弱边缘。\n"
        "  Canny算法通过检测图像灰度梯度的突变来定位边缘。\n"
        "\n"
        "【原理】Canny使用双阈值策略：\n"
        "  - 梯度值 > 高阈值：确定为强边缘\n"
        "  - 低阈值 < 梯度值 < 高阈值：仅当与强边缘相连时保留\n"
        "  - 梯度值 < 低阈值：直接丢弃\n"
        "  低阈值越低，保留的弱边缘越多，可能增加误检；\n"
        "  低阈值越高，过滤越严格，可能丢失真实边缘。\n"
        "\n"
        "【建议】\n"
        "  • 漏检多：降低到 20-30\n"
        "  • 误检多：提高到 70-100\n"
        "  • 通常为高阈值的 1/2 到 1/3"
    ),
    "Canny高阈值": (
        "【作用】Canny边缘检测的高阈值，用于确定强边缘。\n"
        "  强边缘是确定的边缘点，作为后续边缘连接的种子点。\n"
        "\n"
        "【原理】Canny算法使用Sobel算子计算图像的梯度幅值和方向：\n"
        "  - 梯度幅值表示灰度变化的强度\n"
        "  - 高阈值用于筛选出最可靠的边缘点（强边缘）\n"
        "  - 然后通过非极大值抑制细化边缘宽度到1像素\n"
        "  - 最后通过滞后阈值（双阈值）连接边缘\n"
        "  高阈值越高，只保留最明显的边缘，可能丢失细节。\n"
        "\n"
        "【建议】\n"
        "  • 漏检多：降低到 100-120\n"
        "  • 误检多：提高到 200-250\n"
        "  • 通常为低阈值的 2 到 3 倍"
    ),
    "霍夫阈值": (
        "【作用】霍夫变换检测直线的累加器阈值，决定直线检测的严格程度。\n"
        "  霍夫变换是将图像空间中的直线转换为参数空间中的点的技术。\n"
        "\n"
        "【原理】对于边缘图上的每个点，霍夫变换在参数空间中绘制一条曲线：\n"
        "  - 参数空间使用极坐标 (ρ, θ) 表示直线\n"
        "  - 同一条直线上的多个点会在参数空间中交于同一点\n"
        "  - 交点的累加值（得票数）反映了这条直线的支持程度\n"
        "  - 阈值决定了需要多少票才认为这是一条有效直线\n"
        "  使用概率霍夫变换（HoughLinesP）可以得到线段的端点坐标。\n"
        "\n"
        "【建议】\n"
        "  • 漏检多：降低到 30-40\n"
        "  • 误检多：提高到 70-100\n"
        "  • 值越高要求越多边缘点支持"
    ),
    "最小长度": (
        "【作用】过滤掉短于此长度的线段，减少噪声线段的干扰。\n"
        "  霍夫变换可能检测到很多短线段，其中大部分是噪声。\n"
        "\n"
        "【原理】计算每条线段两个端点之间的欧几里得距离：\n"
        "  length = sqrt((x2-x1)² + (y2-y1)²)\n"
        "  如果线段长度小于min_line_length，则该线段被丢弃。\n"
        "  这个参数应该根据实际焊缝的预期长度来设置：\n"
        "  - 如果焊缝较短（如点焊），需要降低此值\n"
        "  - 如果焊缝较长（如连续焊缝），可以提高此值过滤噪声\n"
        "\n"
        "【建议】\n"
        "  • 检测短线段：降低到 20-30\n"
        "  • 过滤噪声线段：提高到 80-100\n"
        "  • 根据实际焊缝长度调整"
    ),
    "最大线段间隔": (
        "【作用】允许合并的线段之间的最大间隔，用于连接断裂的线段。\n"
        "  由于光照、污渍等原因，一条完整的焊缝可能被检测为多段。\n"
        "\n"
        "【原理】在合并线段时，检查两条线段端点之间的最小距离：\n"
        "  - 计算每条线段的中点坐标\n"
        "  - 计算两个中点之间的欧几里得距离\n"
        "  - 如果距离 < max_line_gap，且角度差在容差范围内，\n"
        "    则将两条线段合并为一条\n"
        "  合并后的线段取最远的两个端点作为新线段的端点。\n"
        "\n"
        "【建议】\n"
        "  • 焊缝断裂多：增大到 15-20\n"
        "  • 需要精确线段：降低到 5-8\n"
        "  • 值过大会合并无关线段"
    ),
    "角度容差": (
        "【作用】线段合并时允许的角度偏差范围，控制方向一致性。\n"
        "  焊缝通常是直线或平滑曲线，方向变化不会太大。\n"
        "\n"
        "【原理】计算两条线段的夹角差：\n"
        "  - 每条线段的角度 = arctan2(dy, dx)，范围[-180°, 180°]\n"
        "  - 角度差 = |angle1 - angle2|\n"
        "  - 如果角度差 > 180°，则取 360° - 角度差\n"
        "  - 只有角度差 ≤ angle_tolerance 时，才考虑合并\n"
        "  这确保了只有方向相近的线段才会被合并，\n"
        "  避免将不同方向的线段错误地连接在一起。\n"
        "\n"
        "【建议】\n"
        "  • 严格水平/垂直焊缝：保持 10-15 度\n"
        "  • 倾斜或弯曲焊缝：增大到 20-30 度\n"
        "  • 值过大会合并不同方向的线段"
    ),
}


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
    profile_changed = pyqtSignal(str)  # 参数模板切换
    new_profile_clicked = pyqtSignal()  # 新建参数模板
    save_profile_clicked = pyqtSignal()  # 保存参数模板
    delete_profile_clicked = pyqtSignal()  # 删除参数模板
    auto_save_toggled = pyqtSignal(bool)  # 自动保存开关
    open_saved_folder = pyqtSignal()  # 打开保存文件夹
    camera_changed = pyqtSignal(int)  # 摄像头切换
    open_source_folder = pyqtSignal(str)  # 打开源文件夹 (video/image)

    def __init__(self, parent=None):
        """初始化控制面板"""
        super().__init__(parent)
        self._param_label_min_width = 0
        self._profile_wrap_threshold = 0
        self._value_box_width = 0
        self._init_ui()
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if (
                obj is not self.profile_combo.view().viewport()
                and obj is not self.profile_combo.lineEdit()
            ):
                self.profile_combo.lineEdit().clearFocus()
        return super().eventFilter(obj, event)

    def _init_ui(self):
        """初始化界面"""
        self._param_label_min_width = self._calculate_param_label_width()
        self._value_box_width = self._calculate_value_box_width()
        layout = QVBoxLayout(self)

        # 输入源选择
        source_group = QGroupBox("输入源")
        source_layout = QVBoxLayout()

        self.source_combo = QComboBox()
        self.source_combo.addItems(["摄像头", "视频文件", "图像文件"])
        self.source_combo.currentTextChanged.connect(self._on_source_changed)

        self.camera_combo = QComboBox()
        self.camera_combo.currentIndexChanged.connect(self._on_camera_changed)
        self.camera_combo.hide()

        self.source_folder_button = QPushButton("📂")
        self.source_folder_button.setFixedWidth(36)
        self.source_folder_button.clicked.connect(self._on_open_source_folder)
        self.source_folder_button.hide()

        # 图片浏览按钮
        self.prev_button = QPushButton("上一张")
        self.prev_button.setEnabled(False)
        self.prev_button.clicked.connect(self.prev_image_clicked.emit)
        self.prev_button.setFocusPolicy(Qt.NoFocus)
        self.next_button = QPushButton("下一张")
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self.next_image_clicked.emit)
        self.next_button.setFocusPolicy(Qt.NoFocus)

        source_row = QHBoxLayout()
        source_row.addWidget(self.source_combo, 3)
        source_row.addWidget(self.camera_combo, 1)
        source_row.addWidget(self.source_folder_button, 0)
        source_layout.addLayout(source_row)

        browse_layout = QHBoxLayout()
        browse_layout.addWidget(self.prev_button)
        browse_layout.addWidget(self.next_button)
        source_layout.addLayout(browse_layout)

        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        # 检测参数（合并预处理+检测）
        params_group = QGroupBox("检测参数")
        params_layout = QVBoxLayout()

        # 参数模板（最上面）
        profile_layout = QVBoxLayout()
        profile_layout.setSpacing(4)
        self.profile_section_layout = profile_layout
        profile_top_row = QHBoxLayout()
        profile_top_row.setSpacing(6)
        self.profile_single_row = QHBoxLayout()
        self.profile_single_row.setSpacing(6)
        self.profile_combo = QComboBox()
        self.profile_combo.setEditable(True)
        self.profile_combo.setMinimumWidth(90)
        self.profile_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.profile_combo.currentTextChanged.connect(self.profile_changed.emit)
        self.new_profile_button = QPushButton("新建")
        self.new_profile_button.clicked.connect(self.new_profile_clicked.emit)
        self.save_profile_button = QPushButton("保存")
        self.save_profile_button.clicked.connect(self.save_profile_clicked.emit)
        self.delete_profile_button = QPushButton("删除")
        self.delete_profile_button.clicked.connect(self.delete_profile_clicked.emit)
        self.new_profile_button.setMinimumWidth(52)
        self.new_profile_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.save_profile_button.setMinimumWidth(52)
        self.save_profile_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.delete_profile_button.setMinimumWidth(52)
        self.delete_profile_button.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        profile_button_row = QHBoxLayout()
        profile_button_row.setSpacing(4)
        profile_button_row.addStretch()
        profile_button_row.addWidget(self.new_profile_button)
        profile_button_row.addWidget(self.save_profile_button)
        profile_button_row.addWidget(self.delete_profile_button)
        self.profile_label = QLabel("模板:")
        self.profile_single_row.addWidget(self.profile_label)
        self.profile_single_row.addWidget(self.profile_combo, 1)
        self.profile_single_row.addWidget(self.new_profile_button)
        self.profile_single_row.addWidget(self.save_profile_button)
        self.profile_single_row.addWidget(self.delete_profile_button)
        profile_top_row.addWidget(QLabel("模板:"))
        profile_top_row.addWidget(self.profile_combo, 1)
        self.profile_top_row = profile_top_row
        self.profile_button_row = profile_button_row
        self._profile_wrap_threshold = (
            self.profile_label.sizeHint().width()
            + self.profile_combo.minimumWidth()
            + self.new_profile_button.minimumWidth()
            + self.save_profile_button.minimumWidth()
            + self.delete_profile_button.minimumWidth()
            + 32
        )
        self._rebuild_profile_layout(force_wrap=False)
        params_layout.addLayout(profile_layout)

        # 预处理参数
        self.blur_slider = self._create_slider(
            "模糊核大小", 1, 31, 5, 2, tooltip=PARAM_TOOLTIPS.get("模糊核大小")
        )
        self.clahe_slider = self._create_double_slider(
            "CLAHE限制", 0.1, 10.0, 2.0, 0.1, tooltip=PARAM_TOOLTIPS.get("CLAHE限制")
        )

        params_layout.addWidget(self.blur_slider)
        params_layout.addWidget(self.clahe_slider)

        # 检测参数
        self.canny_low_slider = self._create_slider(
            "Canny低阈值", 0, 255, 50, 5, tooltip=PARAM_TOOLTIPS.get("Canny低阈值")
        )
        self.canny_high_slider = self._create_slider(
            "Canny高阈值", 0, 255, 150, 5, tooltip=PARAM_TOOLTIPS.get("Canny高阈值")
        )
        self.hough_slider = self._create_slider(
            "霍夫阈值", 1, 200, 50, 5, tooltip=PARAM_TOOLTIPS.get("霍夫阈值")
        )
        self.min_length_slider = self._create_slider(
            "最小长度", 10, 500, 50, 10, tooltip=PARAM_TOOLTIPS.get("最小长度")
        )
        self.max_gap_slider = self._create_slider(
            "最大线段间隔", 1, 100, 10, 1, tooltip=PARAM_TOOLTIPS.get("最大线段间隔")
        )
        self.angle_tolerance_slider = self._create_slider(
            "角度容差", 1, 90, 15, 1, tooltip=PARAM_TOOLTIPS.get("角度容差")
        )

        params_layout.addWidget(self.canny_low_slider)
        params_layout.addWidget(self.canny_high_slider)
        params_layout.addWidget(self.hough_slider)
        params_layout.addWidget(self.min_length_slider)
        params_layout.addWidget(self.max_gap_slider)
        params_layout.addWidget(self.angle_tolerance_slider)

        # 恢复默认参数（最下面）
        self.reset_button = QPushButton("恢复默认参数")
        self.reset_button.clicked.connect(self.reset_params_clicked.emit)
        self.reset_button.clicked.connect(
            lambda: self.profile_combo.lineEdit().clearFocus()
        )
        params_layout.addWidget(self.reset_button)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

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

        self.show_original_check.stateChanged.connect(
            lambda: self.display_option_changed.emit()
        )
        self.show_processed_check.stateChanged.connect(
            lambda: self.display_option_changed.emit()
        )
        self.show_edges_check.stateChanged.connect(
            lambda: self.display_option_changed.emit()
        )

        # 检测按钮 + 自动保存 + 打开文件夹（紧凑排列）
        detect_row = QHBoxLayout()
        detect_row.setSpacing(3)
        self.detect_button = QPushButton("开始检测")
        self.detect_button.clicked.connect(self.detect_clicked.emit)
        self.detect_button.clicked.connect(
            lambda: self.profile_combo.lineEdit().clearFocus()
        )
        self.auto_save_check = QCheckBox("自动保存")
        self.auto_save_check.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.auto_save_check.stateChanged.connect(
            lambda state: self.auto_save_toggled.emit(state == Qt.Checked)
        )
        self.open_folder_button = QPushButton("📂")
        self.open_folder_button.setFixedWidth(36)
        self.open_folder_button.clicked.connect(self.open_saved_folder.emit)
        detect_row.addWidget(self.detect_button, 1)
        detect_row.addWidget(self.auto_save_check)
        detect_row.addWidget(self.open_folder_button)
        layout.addLayout(detect_row)

        # 初始化摄像头选项（默认输入源为摄像头）
        self._on_source_changed("摄像头")

        layout.addStretch()

    def _calculate_param_label_width(self) -> int:
        """根据当前字体计算参数标签的最小宽度。"""
        metrics = self.fontMetrics()
        labels = [
            "模糊核大小",
            "CLAHE限制",
            "Canny低阈值",
            "Canny高阈值",
            "霍夫阈值",
            "最小长度",
            "最大线段间隔",
            "角度容差",
        ]
        return max(100, max(metrics.horizontalAdvance(text) for text in labels) + 0)

    def _calculate_value_box_width(self) -> int:
        """计算参数输入框统一宽度，避免整数/浮点输入框错位。"""
        metrics = self.fontMetrics()
        text_width = max(
            metrics.horizontalAdvance("500"),
            metrics.horizontalAdvance("10.00"),
        )
        button_and_frame_padding = 22
        return max(74, text_width + button_and_frame_padding)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rebuild_profile_layout(
            force_wrap=self.width() < self._profile_wrap_threshold
        )

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            child_layout = item.layout()
            if child_layout is not None:
                self._clear_layout(child_layout)

    def _rebuild_profile_layout(self, force_wrap: bool):
        self._clear_layout(self.profile_section_layout)
        self._clear_layout(self.profile_single_row)
        self._clear_layout(self.profile_top_row)
        self._clear_layout(self.profile_button_row)
        if force_wrap:
            self.profile_top_row.addWidget(self.profile_label)
            self.profile_top_row.addWidget(self.profile_combo, 1)
            self.profile_button_row.addStretch()
            self.profile_button_row.addWidget(self.new_profile_button)
            self.profile_button_row.addWidget(self.save_profile_button)
            self.profile_button_row.addWidget(self.delete_profile_button)
            self.profile_section_layout.addLayout(self.profile_top_row)
            self.profile_section_layout.addLayout(self.profile_button_row)
        else:
            self.profile_single_row.addWidget(self.profile_label)
            self.profile_single_row.addWidget(self.profile_combo, 1)
            self.profile_single_row.addWidget(self.new_profile_button)
            self.profile_single_row.addWidget(self.save_profile_button)
            self.profile_single_row.addWidget(self.delete_profile_button)
            self.profile_section_layout.addLayout(self.profile_single_row)

    def _create_slider(
        self,
        label: str,
        min_val: int,
        max_val: int,
        default: int,
        step: int = 1,
        tooltip: str = None,
    ) -> QWidget:
        """创建滑块控件"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        label_widget = QLabel(label)
        label_widget.setMinimumWidth(self._param_label_min_width)
        label_widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        # 设置提示信息
        if tooltip:
            label_widget.setToolTip(tooltip)

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default)
        slider.setSingleStep(step)

        spin = QSpinBox()
        spin.setMinimum(min_val)
        spin.setMaximum(max_val)
        spin.setValue(default)
        spin.setFixedWidth(self._value_box_width)

        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        slider.valueChanged.connect(
            lambda v, name=label: self.param_changed.emit(name, v)
        )

        layout.addWidget(label_widget)
        layout.addWidget(slider, 1)
        layout.addWidget(spin)

        return widget

    def _create_double_slider(
        self,
        label: str,
        min_val: float,
        max_val: float,
        default: float,
        step: float = 0.1,
        tooltip: str = None,
    ) -> QWidget:
        """创建浮点数滑块控件"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        label_widget = QLabel(label)
        label_widget.setMinimumWidth(self._param_label_min_width)
        label_widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        # 设置提示信息
        if tooltip:
            label_widget.setToolTip(tooltip)

        factor = int(1.0 / step) if step < 1 else 1

        spin = QDoubleSpinBox()
        spin.setMinimum(min_val)
        spin.setMaximum(max_val)
        spin.setValue(default)
        spin.setSingleStep(step)
        spin.setDecimals(max(0, len(f"{step:.10f}".rstrip("0").split(".")[-1])))
        spin.setFixedWidth(self._value_box_width)

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(int(min_val * factor))
        slider.setMaximum(int(max_val * factor))
        slider.setValue(int(default * factor))
        slider.setSingleStep(1)

        spin.valueChanged.connect(
            lambda v, s=slider, f=factor: s.setValue(int(round(v * f)))
        )
        slider.valueChanged.connect(lambda v, sp=spin, f=factor: sp.setValue(v / f))
        spin.valueChanged.connect(
            lambda v, name=label: self.param_changed.emit(name, v)
        )
        slider.valueChanged.connect(
            lambda v, name=label, f=factor: self.param_changed.emit(name, v / f)
        )

        layout.addWidget(label_widget)
        layout.addWidget(slider, 1)
        layout.addWidget(spin)

        return widget

    def _on_source_changed(self, text: str):
        """输入源改变处理"""
        source_map = {"摄像头": "camera", "视频文件": "video", "图像文件": "image"}
        source = source_map.get(text, "camera")
        if source in ("video", "image"):
            self.source_folder_button.show()
        else:
            self.source_folder_button.hide()
        if source == "camera":
            from ..input_sources.camera_source import CameraSource

            cameras = CameraSource.list_cameras()
            self.camera_combo.blockSignals(True)
            self.camera_combo.clear()
            if cameras:
                for cam_id in cameras:
                    self.camera_combo.addItem(f"摄像头 {cam_id}", cam_id)
                self.camera_combo.setCurrentIndex(0)
            else:
                self.camera_combo.addItem("未检测到摄像头", -1)
            self.camera_combo.blockSignals(False)
            self.camera_combo.show()
        else:
            self.camera_combo.hide()
        self.source_changed.emit(source)

    @pyqtSlot(int)
    def _on_camera_changed(self, index: int):
        """摄像头切换"""
        cam_id = self.camera_combo.itemData(index)
        if cam_id >= 0:
            self.camera_changed.emit(cam_id)

    @pyqtSlot()
    def _on_open_source_folder(self):
        """打开当前输入源的文件夹"""
        idx = self.source_combo.currentIndex()
        text = self.source_combo.currentText()
        source_map = {"摄像头": "camera", "视频文件": "video", "图像文件": "image"}
        src = source_map.get(text, "")
        if src in ("video", "image"):
            self.open_source_folder.emit(src)

    def get_params(self) -> Dict[str, Any]:
        """获取当前参数"""
        return {
            "blur_kernel_size": self.blur_slider.findChild(QSlider).value(),
            "canny_low": self.canny_low_slider.findChild(QSlider).value(),
            "canny_high": self.canny_high_slider.findChild(QSlider).value(),
            "hough_threshold": self.hough_slider.findChild(QSlider).value(),
            "min_line_length": self.min_length_slider.findChild(QSlider).value(),
            "max_line_gap": self.max_gap_slider.findChild(QSlider).value(),
            "angle_tolerance": self.angle_tolerance_slider.findChild(QSlider).value(),
        }

    def set_params(self, params: Dict[str, Any]):
        """设置参数"""
        if "blur_kernel_size" in params:
            self.blur_slider.findChild(QSlider).setValue(
                int(params["blur_kernel_size"])
            )
        if "canny_low" in params:
            self.canny_low_slider.findChild(QSlider).setValue(int(params["canny_low"]))
        if "canny_high" in params:
            self.canny_high_slider.findChild(QSlider).setValue(
                int(params["canny_high"])
            )
        if "hough_threshold" in params:
            self.hough_slider.findChild(QSlider).setValue(
                int(params["hough_threshold"])
            )
        if "min_line_length" in params:
            self.min_length_slider.findChild(QSlider).setValue(
                int(params["min_line_length"])
            )
        if "max_line_gap" in params:
            self.max_gap_slider.findChild(QSlider).setValue(int(params["max_line_gap"]))
        if "angle_tolerance" in params:
            self.angle_tolerance_slider.findChild(QSlider).setValue(
                int(params["angle_tolerance"])
            )

    def reset_to_defaults(self):
        """重置所有参数为默认值"""
        defaults = {
            "blur_kernel_size": 5,
            "canny_low": 50,
            "canny_high": 150,
            "hough_threshold": 50,
            "min_line_length": 50,
            "max_line_gap": 10,
            "angle_tolerance": 15,
        }
        self.set_params(defaults)

    def get_display_options(self) -> Dict[str, bool]:
        """获取显示选项状态"""
        return {
            "show_original": self.show_original_check.isChecked(),
            "show_processed": self.show_processed_check.isChecked(),
            "show_edges": self.show_edges_check.isChecked(),
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
