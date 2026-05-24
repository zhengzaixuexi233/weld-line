"""
摄像头输入源模块

处理摄像头实时捕获。
遵循 OpenCV 最佳实践：正确释放资源、使用上下文管理器。
"""

import cv2
import numpy as np
import logging
from typing import Optional, Tuple

# 配置日志
logger = logging.getLogger(__name__)


class CameraSource:
    """摄像头输入源
    
    支持USB摄像头和网络摄像头。
    遵循 OpenCV 最佳实践：使用上下文管理器确保资源释放。
    
    Attributes:
        camera_id: 摄像头ID或URL
        cap: OpenCV视频捕获对象
        width: 帧宽度
        height: 帧高度
        fps: 帧率
    """
    
    def __init__(
        self,
        camera_id: int = 0,
        resolution: Optional[Tuple[int, int]] = None,
        fps: int = 30
    ):
        """初始化摄像头源
        
        Args:
            camera_id: 摄像头ID（0为默认摄像头）
            resolution: 分辨率 (宽度, 高度)，None使用默认
            fps: 目标帧率
        """
        self.camera_id = camera_id
        self.cap: Optional[cv2.VideoCapture] = None
        self.width: int = 0
        self.height: int = 0
        self.fps: int = fps
        self._resolution = resolution
        self._frame_count = 0
        
        logger.info(f"CameraSource 初始化: camera_id={camera_id}, "
                   f"resolution={resolution}, fps={fps}")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口（确保资源释放）"""
        self.release()
        return False
    
    def open(self) -> bool:
        """打开摄像头
        
        Returns:
            是否打开成功
        """
        if self.cap is not None:
            self.release()
        
        logger.info(f"正在打开摄像头 {self.camera_id}...")
        self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            logger.error(f"无法打开摄像头 {self.camera_id}")
            return False
        
        # 设置分辨率
        if self._resolution:
            self.width, self.height = self._resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        else:
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 设置帧率
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        
        logger.info(f"摄像头已打开: {self.width}x{self.height} @ {self.fps}fps")
        return True
    
    def get_frame(self) -> Optional[np.ndarray]:
        """获取一帧
        
        Returns:
            帧图像，错误返回None
        """
        if self.cap is None or not self.cap.isOpened():
            logger.warning("摄像头未打开，无法获取帧")
            return None
        
        ret, frame = self.cap.read()
        if ret:
            self._frame_count += 1
            return frame
        
        logger.warning("无法读取帧")
        return None
    
    def get_frame_count(self) -> int:
        """获取已捕获帧数
        
        Returns:
            已捕获帧数
        """
        return self._frame_count
    
    def get_resolution(self) -> Optional[Tuple[int, int]]:
        """获取分辨率
        
        Returns:
            (宽度, 高度) 元组
        """
        return (self.width, self.height) if self.width > 0 else None
    
    def get_fps(self) -> int:
        """获取帧率
        
        Returns:
            帧率
        """
        return self.fps
    
    def is_opened(self) -> bool:
        """检查摄像头是否已打开
        
        Returns:
            是否已打开
        """
        return self.cap is not None and self.cap.isOpened()
    
    def set_resolution(self, width: int, height: int) -> bool:
        """设置分辨率
        
        Args:
            width: 宽度
            height: 高度
            
        Returns:
            是否设置成功
        """
        if self.cap is None:
            logger.warning("摄像头未打开，无法设置分辨率")
            return False
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # 验证设置
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if actual_width == width and actual_height == height:
            self.width = width
            self.height = height
            logger.info(f"分辨率已设置为: {width}x{height}")
            return True
        
        logger.warning(f"分辨率设置失败: 期望 {width}x{height}, "
                      f"实际 {actual_width}x{actual_height}")
        return False
    
    def release(self):
        """释放资源（遵循 OpenCV 最佳实践）"""
        if self.cap is not None:
            logger.info(f"释放摄像头资源 (已捕获 {self._frame_count} 帧)")
            self.cap.release()
            self.cap = None
            self._frame_count = 0
    
    @staticmethod
    def list_cameras() -> list:
        """列出可用摄像头
        
        Returns:
            摄像头ID列表
        """
        cameras = []
        logger.info("正在扫描可用摄像头...")
        
        for i in range(10):  # 检查前10个ID
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cameras.append(i)
                cap.release()
                logger.info(f"发现摄像头: ID={i}")
        
        if not cameras:
            logger.warning("未发现可用摄像头")
        
        return cameras
