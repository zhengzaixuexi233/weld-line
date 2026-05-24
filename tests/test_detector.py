"""
焊缝检测器测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from src.core.detector import WeldDetector
from src.core.preprocessing import ImagePreprocessor


def test_preprocessing():
    """测试预处理功能"""
    preprocessor = ImagePreprocessor()
    
    # 创建测试图像
    test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    
    # 测试灰度转换
    gray = preprocessor.to_grayscale(test_image)
    assert len(gray.shape) == 2, "灰度转换失败"
    
    # 测试高斯模糊
    blurred = preprocessor.apply_gaussian_blur(gray)
    assert blurred.shape == gray.shape, "高斯模糊失败"
    
    # 测试CLAHE
    enhanced = preprocessor.apply_clahe(gray)
    assert enhanced.shape == gray.shape, "CLAHE失败"
    
    print("[OK] 预处理测试通过")


def test_detector():
    """测试检测器功能"""
    detector = WeldDetector()
    
    # 创建带有直线的测试图像
    test_image = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.line(test_image, (50, 100), (150, 100), (255, 255, 255), 2)
    
    # 检测
    detections, processed, edges = detector.detect(test_image)
    
    # 验证
    assert isinstance(detections, list), "检测结果应为列表"
    assert processed is not None, "处理图像不应为空"
    assert edges is not None, "边缘图像不应为空"
    
    print(f"[OK] 检测器测试通过，检测到 {len(detections)} 条线段")


def test_config():
    """测试配置管理"""
    from src.config.manager import ConfigManager
    
    config = ConfigManager()
    
    # 测试获取配置
    blur_size = config.get('preprocessing.blur_kernel_size')
    assert blur_size == 5, f"默认模糊核大小应为5，实际为{blur_size}"
    
    # 测试设置配置
    config.set('preprocessing.blur_kernel_size', 7)
    assert config.get('preprocessing.blur_kernel_size') == 7, "配置设置失败"
    
    print("[OK] 配置管理测试通过")


if __name__ == "__main__":
    test_preprocessing()
    test_detector()
    test_config()
    print("\n[OK] 所有测试通过！")
