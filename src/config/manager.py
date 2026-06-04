"""
配置管理模块

使用YAML文件管理检测参数。
"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from copy import deepcopy
from datetime import datetime


class ConfigManager:
    """配置管理器
    
    管理YAML配置文件，支持加载、保存、更新参数。
    支持参数模板的创建、删除、切换和持久化。
    
    Attributes:
        config_path: 配置文件路径
        config: 当前配置字典
        profiles_path: 参数模板文件路径
        profiles: 参数模板字典
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
        self.profiles: Dict[str, Dict[str, Any]] = {}
        # 参数模板文件路径（与配置文件同目录）
        self.profiles_path: Optional[Path] = None
        self.log_path: Optional[Path] = None
        if self.config_path:
            # 用户数据存放在 config 同级的 user_data 目录，与应用配置分离
            user_data_dir = self.config_path.parent / "user_data"
            self.profiles_path = user_data_dir / "profiles.yaml"
            self.log_path = user_data_dir / "profiles_log.yaml"
            self._migrate_old_profiles()
            self._load_profiles()
        
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

    # ========== 参数模板管理 ==========

    def _migrate_old_profiles(self):
        """首次升级时将 config/ 下旧的 profiles 迁移到 config/user_data/，并清理旧文件"""
        if self.profiles_path is None:
            return
        if self.profiles_path.exists():
            return  # 新位置已有文件，不迁移
        old_profiles = self.config_path.parent / "profiles.yaml" if self.config_path else None
        old_log = self.config_path.parent / "profiles_log.yaml" if self.config_path else None
        if old_profiles and old_profiles.exists():
            self.profiles_path.parent.mkdir(parents=True, exist_ok=True)
            old_profiles.rename(self.profiles_path)
            if old_log and old_log.exists():
                old_log.rename(self.log_path)
            # 删除已成空目录的旧 user_data（如果之前误建了根目录的）
            stale_root_ud = self.config_path.parent.parent / "user_data" if self.config_path else None
            if stale_root_ud and stale_root_ud.exists():
                import shutil
                shutil.rmtree(stale_root_ud, ignore_errors=True)

    def _load_profiles(self):
        """从文件加载参数模板"""
        if self.profiles_path is None or not self.profiles_path.exists():
            # 初始化默认模板
            self.profiles = {
                "默认": deepcopy(self.DEFAULT_CONFIG.get('detection', {}))
            }
            return
        try:
            with open(self.profiles_path, 'r', encoding='utf-8') as f:
                loaded = yaml.safe_load(f)
            if loaded and isinstance(loaded, dict):
                self.profiles = loaded
            else:
                self.profiles = {"默认": deepcopy(self.DEFAULT_CONFIG.get('detection', {}))}
        except Exception:
            self.profiles = {"默认": deepcopy(self.DEFAULT_CONFIG.get('detection', {}))}

    def _save_profiles(self) -> bool:
        """保存参数模板到文件"""
        if self.profiles_path is None:
            return False
        try:
            self.profiles_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.profiles_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.profiles, f, default_flow_style=False, allow_unicode=True)
            return True
        except Exception as e:
            print(f"保存参数模板失败: {e}")
            return False

    def get_profile_names(self) -> list:
        """获取所有参数模板名称"""
        return list(self.profiles.keys())

    def get_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """获取指定参数模板"""
        return self.profiles.get(name)

    def save_profile(self, name: str, params: Dict[str, Any]) -> bool:
        """保存参数模板
        
        Args:
            name: 模板名称
            params: 检测参数字典
            
        Returns:
            是否保存成功
        """
        self.profiles[name] = deepcopy(params)
        self._log_profile_save(name, params)
        return self._save_profiles()

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        """重命名参数模板
        
        Args:
            old_name: 旧名称
            new_name: 新名称
            
        Returns:
            是否重命名成功
        """
        if old_name in self.profiles:
            self.profiles[new_name] = self.profiles.pop(old_name)
            return self._save_profiles()
        return False

    def delete_profile(self, name: str) -> bool:
        """删除参数模板
        
        Args:
            name: 模板名称
            
        Returns:
            是否删除成功（默认模板不可删除）
        """
        if name in self.profiles and len(self.profiles) > 1:
            del self.profiles[name]
            return self._save_profiles()
        return False

    def _log_profile_save(self, name: str, params: Dict[str, Any]):
        """记录参数模板保存日志
        
        Args:
            name: 模板名称
            params: 参数数据
        """
        if self.log_path is None:
            return
        try:
            # 读取现有日志
            logs = []
            if self.log_path.exists():
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    loaded = yaml.safe_load(f)
                    if loaded and isinstance(loaded, list):
                        logs = loaded
            
            # 添加新日志条目
            log_entry = {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'profile_name': name,
                'params': params
            }
            logs.append(log_entry)
            
            # 保存日志
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, 'w', encoding='utf-8') as f:
                yaml.dump(logs, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            print(f"记录参数模板日志失败: {e}")
