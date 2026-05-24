"""
配置管理模块

使用YAML文件管理检测参数。
"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from copy import deepcopy


class ConfigManager:
    """配置管理器
    
    管理YAML配置文件，支持加载、保存、更新参数。
    
    Attributes:
        config_path: 配置文件路径
        config: 当前配置字典
    """
    
    DEFAULT_CONFIG = {
        'preprocessing': {
            'blur_kernel_size': 5,
            'clahe_clip_limit': 2.0,
            'clahe_grid_size': 8
        },
        'detection': {
            'canny_low': 50,
            'canny_high': 150,
            'hough_threshold': 50,
            'min_line_length': 50,
            'max_line_gap': 10,
            'angle_tolerance': 15
        },
        'display': {
            'line_color': [0, 255, 0],
            'line_thickness': 2,
            'show_original': True,
            'show_processed': True
        },
        'input': {
            'default_source': 'camera',
            'camera_id': 0,
            'video_fps': 30,
            'resolution': None
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化配置管理器
        
        Args:
            config_path: 配置文件路径，None使用默认配置
        """
        self.config_path = Path(config_path) if config_path else None
        self.config: Dict[str, Any] = deepcopy(self.DEFAULT_CONFIG)
        
        if self.config_path and self.config_path.exists():
            self.load()
    
    def load(self, path: Optional[Path] = None) -> bool:
        """加载配置文件
        
        Args:
            path: 配置文件路径，None使用初始化时的路径
            
        Returns:
            是否加载成功
        """
        load_path = path or self.config_path
        if load_path is None:
            return False
        
        try:
            with open(load_path, 'r', encoding='utf-8') as f:
                loaded_config = yaml.safe_load(f)
            
            if loaded_config:
                self._merge_config(self.config, loaded_config)
            
            self.config_path = load_path
            return True
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return False
    
    def save(self, path: Optional[Path] = None) -> bool:
        """保存配置文件
        
        Args:
            path: 保存路径，None使用当前路径
            
        Returns:
            是否保存成功
        """
        save_path = path or self.config_path
        if save_path is None:
            return False
        
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    self.config,
                    f,
                    default_flow_style=False,
                    allow_unicode=True
                )
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键，支持点号分隔（如 'detection.canny_low'）
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """设置配置值
        
        Args:
            key: 配置键，支持点号分隔
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def update(self, updates: Dict[str, Any]):
        """批量更新配置
        
        Args:
            updates: 更新字典
        """
        for key, value in updates.items():
            self.set(key, value)
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """获取配置段
        
        Args:
            section: 段名
            
        Returns:
            配置字典
        """
        return self.config.get(section, {})
    
    def reset(self):
        """重置为默认配置"""
        self.config = deepcopy(self.DEFAULT_CONFIG)
    
    def _merge_config(self, base: dict, update: dict):
        """递归合并配置
        
        Args:
            base: 基础配置
            update: 更新配置
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            配置字典副本
        """
        return deepcopy(self.config)
    
    @staticmethod
    def create_default_config(path: str) -> bool:
        """创建默认配置文件
        
        Args:
            path: 保存路径
            
        Returns:
            是否创建成功
        """
        config_path = Path(path)
        manager = ConfigManager()
        manager.config_path = config_path
        return manager.save()
