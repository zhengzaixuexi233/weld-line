"""
图像预处理模块

提供焊缝检测前的图像预处理功能，包括灰度化、降噪、对比度增强等。
"""

import cv2
import numpy as np
from typing import Tuple, Optional


class ImagePreprocessor:
    """图像预处理器
    
    对输入图像进行预处理，提高焊缝检测的准确性。
    
    Attributes:
        blur_kernel_size: 高斯模糊核大小
        clahe_clip_limit: CLAHE对比度限制
        clahe_grid_size: CLAHE网格大小
    """
    
    def __init__(
        self,
        blur_kernel_size: int = 5,
        clahe_clip_limit: float = 2.0,
        clahe_grid_size: int = 8
    ):
        """初始化预处理器
        
        Args:
            blur_kernel_size: 高斯模糊核大小，必须为奇数
            clahe_clip_limit: CLAHE对比度限制
            clahe_grid_size: CLAHE网格大小
        """
        if blur_kernel_size % 2 == 0:
            blur_kernel_size += 1
        
        self.blur_kernel_size = blur_kernel_size
        self.clahe_clip_limit = clahe_clip_limit
        self.clahe_grid_size = clahe_grid_size
        
        # 创建CLAHE对象
        self.clahe = cv2.createCLAHE(
            clipLimit=self.clahe_clip_limit,
            tileGridSize=(self.clahe_grid_size, self.clahe_grid_size)
        )
    
    def to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """转换为灰度图
        
        Args:
            image: 输入图像（BGR格式）
            
        Returns:
            灰度图像
            
        Raises:
            ValueError: 输入图像为空
        """
        if image is None or image.size == 0:
            raise ValueError("输入图像为空")
        
        if len(image.shape) == 2:
            return image
        
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    def apply_gaussian_blur(
        self,
        image: np.ndarray,
        kernel_size: Optional[int] = None
    ) -> np.ndarray:
        """应用高斯模糊
        
        Args:
            image: 输入图像
            kernel_size: 模糊核大小，None使用默认值
            
        Returns:
            模糊后的图像
        """
        ksize = kernel_size or self.blur_kernel_size
        if ksize % 2 == 0:
            ksize += 1
        
        return cv2.GaussianBlur(image, (ksize, ksize), 0)
    
    def apply_clahe(self, image: np.ndarray) -> np.ndarray:
        """应用CLAHE对比度增强
        
        Args:
            image: 输入灰度图像
            
        Returns:
            增强后的图像
        """
        return self.clahe.apply(image)
    
    def apply_bilateral_filter(
        self,
        image: np.ndarray,
        d: int = 9,
        sigma_color: float = 75,
        sigma_space: float = 75
    ) -> np.ndarray:
        """应用双边滤波
        
        在降噪的同时保留边缘信息。
        
        Args:
            image: 输入图像
            d: 滤波直径
            sigma_color: 颜色空间标准差
            sigma_space: 坐标空间标准差
            
        Returns:
            滤波后的图像
        """
        return cv2.bilateralFilter(image, d, sigma_color, sigma_space)
    
    def apply_morphological_close(
        self,
        image: np.ndarray,
        kernel_size: int = 5,
        iterations: int = 1
    ) -> np.ndarray:
        """应用形态学闭操作
        
        用于连接断开的边缘。
        
        Args:
            image: 输入二值图像
            kernel_size: 结构元素大小
            iterations: 迭代次数
            
        Returns:
            处理后的图像
        """
        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (kernel_size, kernel_size)
        )
        return cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel, iterations=iterations)
    
    def preprocess(
        self,
        image: np.ndarray,
        use_bilateral: bool = False,
        use_morphological: bool = False
    ) -> Tuple[np.ndarray, np.ndarray]:
        """完整预处理流程
        
        Args:
            image: 输入图像（BGR格式）
            use_bilateral: 是否使用双边滤波替代高斯模糊
            use_morphological: 是否应用形态学操作
            
        Returns:
            元组：(灰度图像, 预处理后的图像)
        """
        # 转换为灰度图
        gray = self.to_grayscale(image)
        
        # 降噪
        if use_bilateral:
            blurred = self.apply_bilateral_filter(gray)
        else:
            blurred = self.apply_gaussian_blur(gray)
        
        # 对比度增强
        enhanced = self.apply_clahe(blurred)
        
        # 形态学操作（可选）
        if use_morphological:
            enhanced = self.apply_morphological_close(enhanced)
        
        return gray, enhanced
    
    def update_params(self, **kwargs):
        """更新预处理参数
        
        Args:
            **kwargs: 参数名和值
        """
        if 'blur_kernel_size' in kwargs:
            ksize = kwargs['blur_kernel_size']
            if ksize % 2 == 0:
                ksize += 1
            self.blur_kernel_size = ksize
        
        if 'clahe_clip_limit' in kwargs:
            self.clahe_clip_limit = kwargs['clahe_clip_limit']
            self.clahe = cv2.createCLAHE(
                clipLimit=self.clahe_clip_limit,
                tileGridSize=(self.clahe_grid_size, self.clahe_grid_size)
            )
        
        if 'clahe_grid_size' in kwargs:
            self.clahe_grid_size = kwargs['clahe_grid_size']
            self.clahe = cv2.createCLAHE(
                clipLimit=self.clahe_clip_limit,
                tileGridSize=(self.clahe_grid_size, self.clahe_grid_size)
            )
