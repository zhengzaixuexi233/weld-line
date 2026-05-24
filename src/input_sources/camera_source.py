"""
摄像头输入源模块

处理摄像头实时捕获。
"""

import cv2
import numpy as np
from typing import Optional, Tuple


class CameraSource:
    """摄像头输入源
    
    支持USB摄像头和网络摄像头。
    
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
    
    def open(self) -> bool:
        """打开摄像头
        
        Returns:
            是否打开成功
        """
        if self.cap is not None:
            self.release()
        
        self.cap = cv2.VideoCapture(self.camera_id)
        if not self.cap.isOpened():
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
        
        return True
    
    def get_frame(self) -> Optional[np.ndarray]:
        """获取一帧
        
        Returns:
            帧图像，错误返回None
        """
        if self.cap is None or not self.cap.isOpened():
            return None
        
        ret, frame = self.cap.read()
        if ret:
            return frame
        return None
    
    def get_frame_count(self) -> int:
        """获取帧数
        
        Returns:
            摄像头返回-1表示无限流
        """
        return -1
    
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
            return False
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # 验证设置
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if actual_width == width and actual_height == height:
            self.width = width
            self.height = height
            return True
        return False
    
    def release(self):
        """释放资源"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
    
    @staticmethod
    def list_cameras() -> list:
        """列出可用摄像头
        
        Returns:
            摄像头ID列表
        """
        cameras = []
        for i in range(10):  # 检查前10个ID
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cameras.append(i)
                cap.release()
        return cameras
