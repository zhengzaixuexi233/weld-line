import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSlider,
    QSpinBox,
)

from src.config.manager import ConfigManager
from src.gui.controls import ControlPanel
from src.gui.main_window import MainWindow, ScalableImageLabel


class _FakeCameraSource:
    def __init__(self, camera_id=0):
        self.camera_id = camera_id

    @staticmethod
    def list_cameras():
        return []

    def open(self):
        return False

    def get_frame(self):
        return None

    def release(self):
        return None

    def is_opened(self):
        return False


class _FakeWheelDelta:
    def __init__(self, delta_y):
        self._delta_y = delta_y

    def y(self):
        return self._delta_y


class _FakeWheelEvent:
    def __init__(self, delta_y):
        self._delta = _FakeWheelDelta(delta_y)
        self.accepted = False

    def angleDelta(self):
        return self._delta

    def accept(self):
        self.accepted = True


class ControlPanelLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_profile_section_stays_single_row_by_default(self):
        panel = ControlPanel()
        panel.resize(400, 700)
        panel.show()
        self.app.processEvents()

        self.assertEqual(panel.profile_section_layout.count(), 1)
        self.assertIsInstance(panel.profile_section_layout.itemAt(0).layout(), QHBoxLayout)

    def test_profile_section_wraps_only_when_width_is_too_small(self):
        panel = ControlPanel()
        panel.resize(400, 700)
        panel.show()
        self.app.processEvents()

        panel._profile_wrap_threshold = panel.width() + 1
        panel._rebuild_profile_layout(
            force_wrap=panel.width() < panel._profile_wrap_threshold
        )

        self.assertEqual(panel.profile_section_layout.count(), 2)
        self.assertIsInstance(panel.profile_section_layout.itemAt(0).layout(), QHBoxLayout)
        self.assertIsInstance(panel.profile_section_layout.itemAt(1).layout(), QHBoxLayout)

    def test_parameter_label_uses_adaptive_minimum_width(self):
        panel = ControlPanel()

        label = panel.blur_slider.findChild(QLabel)

        self.assertGreater(label.minimumWidth(), 100)
        self.assertEqual(label.sizePolicy().horizontalPolicy(), QSizePolicy.Minimum)

    def test_parameter_label_width_stays_uniform_but_more_compact(self):
        panel = ControlPanel()
        metrics = panel.fontMetrics()
        longest_text_width = max(
            metrics.horizontalAdvance(text)
            for text in [
                "模糊核大小",
                "CLAHE限制",
                "Canny低阈值",
                "Canny高阈值",
                "霍夫阈值",
                "最小长度",
                "最大线段间隔",
                "角度容差",
            ]
        )

        self.assertGreaterEqual(panel._param_label_min_width, longest_text_width)
        self.assertLessEqual(panel._param_label_min_width, longest_text_width + 10)

    def test_parameter_value_boxes_share_same_width(self):
        panel = ControlPanel()
        panel.show()
        self.app.processEvents()

        blur_spin = panel.blur_slider.findChild(QSpinBox)
        clahe_spin = panel.clahe_slider.findChild(QDoubleSpinBox)

        self.assertIsNotNone(blur_spin)
        self.assertIsNotNone(clahe_spin)
        self.assertEqual(blur_spin.width(), clahe_spin.width())

    def test_panel_does_not_create_extra_visible_spinboxes(self):
        panel = ControlPanel()
        panel.show()
        self.app.processEvents()

        spin_boxes = panel.findChildren(QSpinBox)
        double_spin_boxes = panel.findChildren(QDoubleSpinBox)

        self.assertEqual(len(spin_boxes), 7)
        self.assertEqual(len(double_spin_boxes), 1)

    def test_slider_keeps_visible_width_at_panel_minimum_size(self):
        panel = ControlPanel()
        panel.resize(400, 700)
        panel.show()
        self.app.processEvents()

        blur_slider = panel.blur_slider.findChild(QSlider)

        self.assertIsNotNone(blur_slider)
        self.assertGreaterEqual(blur_slider.width(), 60)


class MainWindowLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @patch("src.gui.main_window.CameraSource", _FakeCameraSource)
    @patch("src.gui.controls.CameraSource", _FakeCameraSource, create=True)
    def test_main_layout_prioritizes_image_area_over_control_panel(self):
        window = MainWindow(ConfigManager())

        self.assertGreaterEqual(window.minimumWidth(), 1240)
        self.assertEqual(window.control_panel.minimumWidth(), 400)
        self.assertLessEqual(window.control_panel.maximumWidth(), 480)
        self.assertGreater(window.centralWidget().layout().stretch(0), 0)
        self.assertGreater(
            window.centralWidget().layout().stretch(0),
            window.centralWidget().layout().stretch(1),
        )

    @patch("src.gui.main_window.CameraSource", _FakeCameraSource)
    @patch("src.gui.controls.CameraSource", _FakeCameraSource, create=True)
    def test_time_labels_keep_adaptive_width(self):
        window = MainWindow(ConfigManager())

        window._create_video_progress()
        adaptive_label = window._build_time_label("00:00 / 00:00")

        self.assertEqual(
            window.video_current_time_label.sizePolicy().horizontalPolicy(),
            QSizePolicy.Minimum,
        )
        self.assertGreaterEqual(
            adaptive_label.minimumWidth(),
            adaptive_label.fontMetrics().horizontalAdvance("00:00 / 00:00"),
        )


class ScalableImageLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_zoom_range_is_limited_to_100_to_300_percent(self):
        label = ScalableImageLabel()
        label.resize(320, 240)
        label.show()
        pixmap = QPixmap(640, 480)
        pixmap.fill()
        label.setPixmap(pixmap)

        for _ in range(20):
            label.wheelEvent(_FakeWheelEvent(120))
        self.assertEqual(label._zoom_factor, 3.0)

        for _ in range(20):
            label.wheelEvent(_FakeWheelEvent(-120))
        self.assertEqual(label._zoom_factor, 1.0)

    def test_live_pixmap_refresh_preserves_zoom_state_when_requested(self):
        label = ScalableImageLabel()
        label.resize(240, 240)
        label.show()
        base_pixmap = QPixmap(640, 640)
        base_pixmap.fill()
        next_pixmap = QPixmap(640, 640)
        next_pixmap.fill()

        label.setPixmap(base_pixmap)
        label.wheelEvent(_FakeWheelEvent(120))
        label.wheelEvent(_FakeWheelEvent(120))
        label._offset = QPointF(24, -18)

        label.setPixmap(next_pixmap, preserve_view=True)

        self.assertAlmostEqual(label._zoom_factor, 1.4)
        self.assertEqual(label._offset, QPointF(24, -18))


if __name__ == "__main__":
    unittest.main()
