"""
可视化工具模块

提供检测结果的可视化功能。
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional


def draw_lines(
    image: np.ndarray,
    lines: list,
    color: Tuple[int, int, int] = (0, 255, 0),
    thickness: int = 2
) -> np.ndarray:
    """在图像上绘制线段
    
    Args:
        image: 输入图像
        lines: 线段列表，每条线段为 (x1, y1, x2, y2) 或类似对象
        color: 线条颜色 (BGR)
        thickness: 线条粗细
        
    Returns:
        绘制后的图像
    """
    result = image.copy()
    
    for line in lines:
        # 支持LineSegment对象或元组
        if hasattr(line, 'x1'):
            x1, y1 = line.x1, line.y1
            x2, y2 = line.x2, line.y2
        else:
            x1, y1, x2, y2 = line[:4]
        
        cv2.line(result, (x1, y1), (x2, y2), color, thickness)
    
    return result


def draw_detections(
    image: np.ndarray,
    detections: list,
    line_color: Tuple[int, int, int] = (0, 255, 0),
    thickness: int = 2,
    show_info: bool = True
) -> np.ndarray:
    """绘制检测结果
    
    Args:
        image: 输入图像
        detections: 检测结果列表
        line_color: 线条颜色
        thickness: 线条粗细
        show_info: 是否显示信息文本
        
    Returns:
        绘制后的图像
    """
    result = draw_lines(image, detections, line_color, thickness)
    
    if show_info and detections:
        # 在左上角显示检测数量
        text = f"Detected: {len(detections)}"
        cv2.putText(
            result,
            text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )
    
    return result


def draw_roi(
    image: np.ndarray,
    roi: Tuple[int, int, int, int],
    color: Tuple[int, int, int] = (255, 0, 0),
    thickness: int = 2
) -> np.ndarray:
    """绘制感兴趣区域
    
    Args:
        image: 输入图像
        roi: 区域 (x, y, width, height)
        color: 线条颜色
        thickness: 线条粗细
        
    Returns:
        绘制后的图像
    """
    result = image.copy()
    x, y, w, h = roi
    cv2.rectangle(result, (x, y), (x + w, y + h), color, thickness)
    return result


def create_side_by_side(
    image1: np.ndarray,
    image2: np.ndarray,
    resize: bool = True
) -> np.ndarray:
    """创建并排对比图
    
    Args:
        image1: 左侧图像
        image2: 右侧图像
        resize: 是否调整大小匹配
        
    Returns:
        并排图像
    """
    if resize:
        h1, w1 = image1.shape[:2]
        h2, w2 = image2.shape[:2]
        
        # 调整到相同高度
        target_h = max(h1, h2)
        if h1 != target_h:
            scale = target_h / h1
            image1 = cv2.resize(image1, (int(w1 * scale), target_h))
        if h2 != target_h:
            scale = target_h / h2
            image2 = cv2.resize(image2, (int(w2 * scale), target_h))
    
    return np.hstack([image1, image2])


def add_text_overlay(
    image: np.ndarray,
    text: str,
    position: Tuple[int, int] = (10, 30),
    font_scale: float = 1.0,
    color: Tuple[int, int, int] = (0, 255, 0),
    thickness: int = 2
) -> np.ndarray:
    """添加文本覆盖
    
    Args:
        image: 输入图像
        text: 文本内容
        position: 位置 (x, y)
        font_scale: 字体大小
        color: 颜色
        thickness: 粗细
        
    Returns:
        添加文本后的图像
    """
    result = image.copy()
    cv2.putText(
        result,
        text,
        position,
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        color,
        thickness
    )
    return result
