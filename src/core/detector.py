"""
焊缝检测器模块

实现基于霍夫变换的直线焊缝检测算法。
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass

from .preprocessing import ImagePreprocessor


@dataclass
class LineSegment:
    """线段数据类
    
    Attributes:
        x1, y1: 起点坐标
        x2, y2: 终点坐标
        length: 线段长度
        angle: 线段角度（度）
    """
    x1: int
    y1: int
    x2: int
    y2: int
    length: float
    angle: float


class WeldDetector:
    """焊缝检测器
    
    使用霍夫变换检测图像中的直线焊缝。
    
    Attributes:
        preprocessor: 图像预处理器
        canny_low: Canny边缘检测低阈值
        canny_high: Canny边缘检测高阈值
        hough_threshold: 霍夫变换阈值
        min_line_length: 最小线段长度
        max_line_gap: 最大线段间隔
        angle_tolerance: 角度容差（度）
    """
    
    def __init__(
        self,
        preprocessor: Optional[ImagePreprocessor] = None,
        canny_low: int = 50,
        canny_high: int = 150,
        hough_threshold: int = 50,
        min_line_length: int = 50,
        max_line_gap: int = 10,
        angle_tolerance: float = 15.0
    ):
        """初始化检测器
        
        Args:
            preprocessor: 图像预处理器，None则使用默认
            canny_low: Canny边缘检测低阈值
            canny_high: Canny边缘检测高阈值
            hough_threshold: 霍夫变换阈值
            min_line_length: 最小线段长度
            max_line_gap: 最大线段间隔
            angle_tolerance: 角度容差（度）
        """
        self.preprocessor = preprocessor or ImagePreprocessor()
        
        self.canny_low = canny_low
        self.canny_high = canny_high
        self.hough_threshold = hough_threshold
        self.min_line_length = min_line_length
        self.max_line_gap = max_line_gap
        self.angle_tolerance = angle_tolerance
    
    def detect_edges(self, image: np.ndarray) -> np.ndarray:
        """检测边缘
        
        Args:
            image: 输入灰度图像
            
        Returns:
            边缘图像
        """
        return cv2.Canny(image, self.canny_low, self.canny_high)
    
    def detect_lines(self, edges: np.ndarray) -> Optional[np.ndarray]:
        """检测直线
        
        使用概率霍夫变换检测直线。
        
        Args:
            edges: 边缘图像
            
        Returns:
            线段数组，每条线段为 [x1, y1, x2, y2]，无检测结果返回None
        """
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=self.hough_threshold,
            minLineLength=self.min_line_length,
            maxLineGap=self.max_line_gap
        )
        return lines
    
    def calculate_line_properties(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int
    ) -> Tuple[float, float]:
        """计算线段属性
        
        Args:
            x1, y1: 起点坐标
            x2, y2: 终点坐标
            
        Returns:
            元组：(长度, 角度)
        """
        length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        return length, angle
    
    def filter_lines(
        self,
        lines: np.ndarray,
        min_length: Optional[float] = None,
        angle_range: Optional[Tuple[float, float]] = None
    ) -> List[LineSegment]:
        """过滤线段
        
        根据长度和角度过滤线段。
        
        Args:
            lines: 原始线段数组
            min_length: 最小长度，None使用默认值
            angle_range: 角度范围 (min, max)，None不过滤角度
            
        Returns:
            过滤后的线段列表
        """
        if lines is None:
            return []
        
        min_len = min_length or self.min_line_length
        filtered = []
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            length, angle = self.calculate_line_properties(x1, y1, x2, y2)
            
            # 长度过滤
            if length < min_len:
                continue
            
            # 角度过滤
            if angle_range is not None:
                min_angle, max_angle = angle_range
                if not (min_angle <= angle <= max_angle):
                    continue
            
            filtered.append(LineSegment(
                x1=x1, y1=y1,
                x2=x2, y2=y2,
                length=length,
                angle=angle
            ))
        
        return filtered
    
    def merge_lines(
        self,
        lines: List[LineSegment],
        distance_threshold: float = 20,
        angle_threshold: float = 10
    ) -> List[LineSegment]:
        """合并相近的线段
        
        Args:
            lines: 线段列表
            distance_threshold: 距离阈值
            angle_threshold: 角度阈值
            
        Returns:
            合并后的线段列表
        """
        if not lines:
            return []
        
        merged = []
        used = [False] * len(lines)
        
        for i, line1 in enumerate(lines):
            if used[i]:
                continue
            
            group = [line1]
            used[i] = True
            
            for j, line2 in enumerate(lines):
                if used[j]:
                    continue
                
                # 检查角度相似性
                angle_diff = abs(line1.angle - line2.angle)
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff
                
                if angle_diff > angle_threshold:
                    continue
                
                # 检查距离
                mid1 = ((line1.x1 + line1.x2) / 2, (line1.y1 + line1.y2) / 2)
                mid2 = ((line2.x1 + line2.x2) / 2, (line2.y1 + line2.y2) / 2)
                dist = np.sqrt((mid1[0] - mid2[0]) ** 2 + (mid1[1] - mid2[1]) ** 2)
                
                if dist < distance_threshold:
                    group.append(line2)
                    used[j] = True
            
            # 合并组中的线段
            if len(group) == 1:
                merged.append(group[0])
            else:
                merged_line = self._merge_line_group(group)
                merged.append(merged_line)
        
        return merged
    
    def _merge_line_group(self, lines: List[LineSegment]) -> LineSegment:
        """合并一组线段
        
        Args:
            lines: 线段列表
            
        Returns:
            合并后的线段
        """
        # 找到最远的两个端点
        points = []
        for line in lines:
            points.append((line.x1, line.y1))
            points.append((line.x2, line.y2))
        
        max_dist = 0
        p1, p2 = points[0], points[1]
        
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                dist = np.sqrt(
                    (points[i][0] - points[j][0]) ** 2 +
                    (points[i][1] - points[j][1]) ** 2
                )
                if dist > max_dist:
                    max_dist = dist
                    p1, p2 = points[i], points[j]
        
        length, angle = self.calculate_line_properties(p1[0], p1[1], p2[0], p2[1])
        
        return LineSegment(
            x1=p1[0], y1=p1[1],
            x2=p2[0], y2=p2[1],
            length=length,
            angle=angle
        )
    
    def detect(
        self,
        image: np.ndarray,
        roi: Optional[Tuple[int, int, int, int]] = None,
        merge: bool = True
    ) -> Tuple[List[LineSegment], np.ndarray, np.ndarray]:
        """检测焊缝
        
        Args:
            image: 输入图像（BGR格式）
            roi: 感兴趣区域 (x, y, width, height)，None处理整幅图像
            merge: 是否合并相近线段
            
        Returns:
            元组：(检测到的线段, 预处理图像, 边缘图像)
        """
        # ROI处理
        if roi is not None:
            x, y, w, h = roi
            roi_image = image[y:y+h, x:x+w]
        else:
            roi_image = image
            x, y = 0, 0
        
        # 预处理
        gray, enhanced = self.preprocessor.preprocess(roi_image)
        
        # 边缘检测
        edges = self.detect_edges(enhanced)
        
        # 直线检测
        raw_lines = self.detect_lines(edges)
        
        # 过滤
        filtered_lines = self.filter_lines(raw_lines)
        
        # 合并
        if merge:
            filtered_lines = self.merge_lines(filtered_lines)
        
        # 调整坐标（如果有ROI偏移）
        if roi is not None:
            for line in filtered_lines:
                line.x1 += x
                line.y1 += y
                line.x2 += x
                line.y2 += y
        
        return filtered_lines, enhanced, edges
    
    def update_params(self, **kwargs):
        """更新检测参数
        
        Args:
            **kwargs: 参数名和值
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # 更新预处理器参数
        preprocessor_params = {
            k: v for k, v in kwargs.items()
            if k.startswith('blur_') or k.startswith('clahe_')
        }
        if preprocessor_params:
            self.preprocessor.update_params(**preprocessor_params)
