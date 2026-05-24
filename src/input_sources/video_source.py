"""
视频输入源模块

处理视频文件的读取和帧获取。
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional


class VideoSource:
    """视频输入源
    
    支持读取视频文件（MP4、AVI等）。
    
    Attributes:
        video_path: 视频文件路径
        cap: OpenCV视频捕获对象
        fps: 视频帧率
        frame_count: 总帧数
        current_frame: 当前帧索引
    """
    
    SUPPORTED_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv'}
    
    def __init__(self, video_path: Optional[str] = None):
        """初始化视频源
        
        Args:
            video_path: 视频文件路径，None则稍后加载
        """
        self.video_path = Path(video_path) if video_path else None
        self.cap: Optional[cv2.VideoCapture] = None
        self.fps: float = 0
        self.frame_count: int = 0
        self.current_frame: int = 0
        
        if self.video_path and self.video_path.exists():
            self.open(self.video_path)
    
    def open(self, path: Path) -> bool:
        """打开视频文件
        
        Args:
            path: 视频文件路径
            
        Returns:
            是否打开成功
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不支持的视频格式
        """
        if not path.exists():
            raise FileNotFoundError(f"视频文件不存在: {path}")
        
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(f"不支持的视频格式: {path.suffix}")
        
        if self.cap is not None:
            self.release()
        
        self.cap = cv2.VideoCapture(str(path))
        if not self.cap.isOpened():
            raise ValueError(f"无法打开视频: {path}")
        
        self.video_path = path
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame = 0
        
        return True
    
    def get_frame(self) -> Optional[np.ndarray]:
        """获取下一帧
        
        Returns:
            帧图像，结束或错误返回None
        """
        if self.cap is None or not self.cap.isOpened():
            return None
        
        ret, frame = self.cap.read()
        if ret:
            self.current_frame += 1
            return frame
        return None
    
    def seek(self, frame_number: int) -> bool:
        """跳转到指定帧
        
        Args:
            frame_number: 目标帧号
            
        Returns:
            是否跳转成功
        """
        if self.cap is None:
            return False
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self.current_frame = frame_number
        return True
    
    def get_frame_count(self) -> int:
        """获取总帧数
        
        Returns:
            视频总帧数
        """
        return self.frame_count
    
    def get_fps(self) -> float:
        """获取帧率
        
        Returns:
            视频帧率
        """
        return self.fps
    
    def get_resolution(self) -> Optional[tuple]:
        """获取视频分辨率
        
        Returns:
            (宽度, 高度) 元组
        """
        if self.cap is None:
            return None
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (width, height)
    
    def is_opened(self) -> bool:
        """检查视频是否已打开
        
        Returns:
            是否已打开
        """
        return self.cap is not None and self.cap.isOpened()
    
    def get_progress(self) -> float:
        """获取播放进度
        
        Returns:
            进度百分比 (0-100)
        """
        if self.frame_count == 0:
            return 0
        return (self.current_frame / self.frame_count) * 100
    
    def release(self):
        """释放资源"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.current_frame = 0
