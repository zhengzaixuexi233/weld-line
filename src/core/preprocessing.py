"""
图像预处理模块

提供焊缝检测前的图像预处理功能，包括灰度化、降噪、对比度增强等。
遵循 computer-vision-opencv 技能的最佳实践。
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional

# 配置日志
logger = logging.getLogger(__name__)


def validate_image(image: np.ndarray, name: str = "image") -> None:
    """验证图像有效性（遵循 OpenCV 最佳实践）
    
    Args:
        image: 输入图像
        name: 图像名称（用于错误信息）
        
    Raises:
        ValueError: 图像无效
        TypeError: 图像类型错误
    """
    if image is None:
        raise ValueError(f"{name} 为 None")
    
    if not isinstance(image, np.ndarray):
        raise TypeError(f"{name} 必须是 numpy.ndarray，实际类型: {type(image)}")
    
    if len(image.shape) < 2:
        raise ValueError(f"{name} 维度不足: {image.shape}，至少需要2维")
    
    if image.size == 0:
        raise ValueError(f"{name} 为空图像，尺寸为0")
    
    # 检查数据类型
    if image.dtype not in (np.uint8, np.float32, np.float64):
        logger.warning(f"{name} 数据类型为 {image.dtype}，建议使用 uint8 或 float32")


def ensure_uint8(image: np.ndarray) -> np.ndarray:
    """确保图像为 uint8 类型（OpenCV 标准格式）
    
    Args:
        image: 输入图像
        
    Returns:
        uint8 格式的图像
    """
    if image.dtype == np.uint8:
        return image
    
    if image.dtype in (np.float32, np.float64):
        # 假设浮点数范围为 [0, 1] 或 [0, 255]
        if image.max() <= 1.0:
            return (image * 255).astype(np.uint8)
        else:
            return np.clip(image, 0, 255).astype(np.uint8)
    
    # 其他类型，归一化到 [0, 255]
    normalized = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)
    return normalized.astype(np.uint8)


class ImagePreprocessor:
    """图像预处理器
    
    对输入图像进行预处理，提高焊缝检测的准确性。
    遵循 OpenCV 最佳实践：验证输入、正确处理色彩空间、使用适当的数据类型。
    
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
        # 确保核大小为奇数
        if blur_kernel_size % 2 == 0:
            blur_kernel_size += 1
            logger.info(f"模糊核大小调整为奇数: {blur_kernel_size}")
        
        self.blur_kernel_size = blur_kernel_size
        self.clahe_clip_limit = clahe_clip_limit
        self.clahe_grid_size = clahe_grid_size
        
        # 创建CLAHE对象
        self.clahe = cv2.createCLAHE(
            clipLimit=self.clahe_clip_limit,
            tileGridSize=(self.clahe_grid_size, self.clahe_grid_size)
        )
        
        logger.debug(f"ImagePreprocessor 初始化: blur={blur_kernel_size}, "
                    f"clahe_clip={clahe_clip_limit}, clahe_grid={clahe_grid_size}")
    
    def to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """转换为灰度图（遵循 OpenCV 色彩空间转换最佳实践）
        
        Args:
            image: 输入图像（BGR格式或灰度图）
            
        Returns:
            灰度图像（uint8 格式）
            
        Raises:
            ValueError: 输入图像为空或格式不正确
        """
        # 验证输入
        validate_image(image, "输入图像")
        
        # 确保 uint8 类型
        image = ensure_uint8(image)
        
        # 已经是灰度图
        if len(image.shape) == 2:
            logger.debug("输入已是灰度图，直接返回")
            return image
        
        # 检查通道数
        if len(image.shape) == 3:
            channels = image.shape[2]
            if channels == 1:
                # 单通道，直接 squeeze
                return image.squeeze()
            elif channels == 3:
                # BGR 转灰度（标准 OpenCV 转换）
                return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            elif channels == 4:
                # BGRA 转灰度
                return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
            else:
                raise ValueError(f"不支持的通道数: {channels}")
        
        raise ValueError(f"不支持的图像形状: {image.shape}")
    
    def apply_gaussian_blur(
        self,
        image: np.ndarray,
        kernel_size: Optional[int] = None
    ) -> np.ndarray:
        """应用高斯模糊（降噪）
        
        Args:
            image: 输入图像
            kernel_size: 模糊核大小，None使用默认值
            
        Returns:
            模糊后的图像
        """
        validate_image(image, "模糊输入图像")
        
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
        validate_image(image, "CLAHE输入图像")
        
        # CLAHE 要求 uint8 类型
        if image.dtype != np.uint8:
            image = ensure_uint8(image)
        
        return self.clahe.apply(image)
    
    def apply_bilateral_filter(
        self,
        image: np.ndarray,
        d: int = 9,
        sigma_color: float = 75,
        sigma_space: float = 75
    ) -> np.ndarray:
        """应用双边滤波（降噪同时保留边缘）
        
        Args:
            image: 输入图像
            d: 滤波直径
            sigma_color: 颜色空间标准差
            sigma_space: 坐标空间标准差
            
        Returns:
            滤波后的图像
        """
        validate_image(image, "双边滤波输入图像")
        return cv2.bilateralFilter(image, d, sigma_color, sigma_space)
    
    def apply_morphological_close(
        self,
        image: np.ndarray,
        kernel_size: int = 5,
        iterations: int = 1
    ) -> np.ndarray:
        """应用形态学闭操作（连接断开的边缘）
        
        Args:
            image: 输入二值图像
            kernel_size: 结构元素大小
            iterations: 迭代次数
            
        Returns:
            处理后的图像
        """
        validate_image(image, "形态学输入图像")
        
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
            logger.info(f"更新模糊核大小: {ksize}")
        
        if 'clahe_clip_limit' in kwargs:
            self.clahe_clip_limit = kwargs['clahe_clip_limit']
            self.clahe = cv2.createCLAHE(
                clipLimit=self.clahe_clip_limit,
                tileGridSize=(self.clahe_grid_size, self.clahe_grid_size)
            )
            logger.info(f"更新CLAHE限制: {self.clahe_clip_limit}")
        
        if 'clahe_grid_size' in kwargs:
            self.clahe_grid_size = kwargs['clahe_grid_size']
            self.clahe = cv2.createCLAHE(
                clipLimit=self.clahe_clip_limit,
                tileGridSize=(self.clahe_grid_size, self.clahe_grid_size)
            )
            logger.info(f"更新CLAHE网格大小: {self.clahe_grid_size}")
