"""
图像输入源模块

处理静态图像文件的读取。
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, List


class ImageSource:
    """图像输入源
    
    支持读取常见图像格式（JPG、PNG、BMP等）。
    
    Attributes:
        image_path: 图像文件路径
        image: 当前加载的图像
    """
    
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
    
    def __init__(self, image_path: Optional[str] = None):
        """初始化图像源
        
        Args:
            image_path: 图像文件路径，None则稍后加载
        """
        self.image_path = Path(image_path) if image_path else None
        self.image: Optional[np.ndarray] = None
        
        if self.image_path and self.image_path.exists():
            self.load(self.image_path)
    
    def load(self, path: Path) -> bool:
        """加载图像
        
        Args:
            path: 图像文件路径
            
        Returns:
            是否加载成功
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不支持的图像格式
        """
        if not path.exists():
            raise FileNotFoundError(f"图像文件不存在: {path}")
        
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(f"不支持的图像格式: {path.suffix}")
        
        self.image = cv2.imread(str(path))
        if self.image is None:
            raise ValueError(f"无法读取图像: {path}")
        
        self.image_path = path
        return True
    
    def get_frame(self) -> Optional[np.ndarray]:
        """获取当前帧
        
        Returns:
            图像数组，未加载返回None
        """
        return self.image
    
    def get_frame_count(self) -> int:
        """获取帧数
        
        Returns:
            图像数量（静态图像为1）
        """
        return 1 if self.image is not None else 0
    
    def get_resolution(self) -> Optional[tuple]:
        """获取图像分辨率
        
        Returns:
            (宽度, 高度) 元组，未加载返回None
        """
        if self.image is None:
            return None
        height, width = self.image.shape[:2]
        return (width, height)
    
    def is_opened(self) -> bool:
        """检查是否已加载图像
        
        Returns:
            是否已加载
        """
        return self.image is not None
    
    def release(self):
        """释放资源"""
        self.image = None
        self.image_path = None
    
    @staticmethod
    def list_images(directory: Path) -> List[Path]:
        """列出目录中的图像文件
        
        Args:
            directory: 目录路径
            
        Returns:
            图像文件路径列表
        """
        images = []
        for ext in ImageSource.SUPPORTED_FORMATS:
            images.extend(directory.glob(f"*{ext}"))
            images.extend(directory.glob(f"*{ext.upper()}"))
        return sorted(set(images))
