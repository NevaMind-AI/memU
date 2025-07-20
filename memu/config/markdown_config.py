"""
MemU Markdown配置系统 - 动态文件夹结构
每个md文件类型都有自己的文件夹，包含config.py和prompt.txt
"""

import os
import importlib.util
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

@dataclass
class MarkdownFileConfig:
    """极简markdown文件配置"""
    
    name: str                          # 文件类型名称
    filename: str                      # 文件名
    description: str                   # 文件描述
    folder_path: str                   # 文件夹路径
    prompt_path: str                   # prompt文件路径


class MarkdownConfigManager:
    """动态加载文件夹配置的管理器"""
    
    def __init__(self):
        self.config_base_dir = Path(__file__).parent
        self._files_config: Dict[str, MarkdownFileConfig] = {}
        self._processing_order: List[str] = []
        self._load_all_configs()
    
    def _load_all_configs(self):
        """动态扫描并加载所有文件夹配置"""
        self._files_config = {}
        
        # 扫描config目录下的所有文件夹
        for item in self.config_base_dir.iterdir():
            if item.is_dir() and item.name not in ['__pycache__', 'prompts']:
                folder_name = item.name
                config_file = item / "config.py"
                prompt_file = item / "prompt.txt"
                
                if config_file.exists():
                    try:
                        # 动态加载配置模块
                        spec = importlib.util.spec_from_file_location(
                            f"{folder_name}_config", 
                            config_file
                        )
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # 获取配置信息
                        if hasattr(module, 'get_file_info'):
                            file_info = module.get_file_info()
                            
                            self._files_config[folder_name] = MarkdownFileConfig(
                                name=file_info["name"],
                                filename=file_info["filename"],
                                description=file_info["description"],
                                folder_path=str(item),
                                prompt_path=str(prompt_file) if prompt_file.exists() else ""
                            )
                            
                    except Exception as e:
                        print(f"警告: 无法加载配置文件夹 {folder_name}: {e}")
        
        self._processing_order = list(self._files_config.keys())
    
    def get_file_config(self, file_type: str) -> Optional[MarkdownFileConfig]:
        """获取指定文件类型的配置"""
        return self._files_config.get(file_type)
    
    def get_all_file_types(self) -> List[str]:
        """获取所有支持的文件类型"""
        return list(self._files_config.keys())
    
    def get_processing_order(self) -> List[str]:
        """获取处理顺序"""
        return self._processing_order.copy()
    
    def get_file_description(self, file_type: str) -> str:
        """获取文件类型的描述"""
        config = self.get_file_config(file_type)
        return config.description if config else ""
    
    def validate_file_type(self, file_type: str) -> bool:
        """验证文件类型是否支持"""
        return file_type in self._files_config
    
    def get_prompt_path(self, file_type: str) -> str:
        """获取prompt文件路径"""
        config = self.get_file_config(file_type)
        return config.prompt_path if config else ""
    
    def get_folder_path(self, file_type: str) -> str:
        """获取文件夹路径"""
        config = self.get_file_config(file_type)
        return config.folder_path if config else ""
    
    def get_file_types_mapping(self) -> Dict[str, str]:
        """获取文件类型到文件名的映射"""
        return {
            name: config.filename 
            for name, config in self._files_config.items()
        }


# 全局配置管理器实例
_config_manager = None

def get_config_manager() -> MarkdownConfigManager:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = MarkdownConfigManager()
    return _config_manager

# 保持向后兼容的API函数

def detect_file_type(filename: str, content: str = "") -> str:
    """根据文件名智能检测文件类型"""
    manager = get_config_manager()
    file_types = manager.get_all_file_types()
    
    if not file_types:
        return "activity"
    
    # 根据文件名关键词检测
    filename_lower = filename.lower()
    
    # 检测profile类型
    if any(keyword in filename_lower for keyword in ['profile', '个人信息', '档案', '简历']):
        if 'profile' in file_types:
            return 'profile'
    
    # 检测event类型
    if any(keyword in filename_lower for keyword in ['event', 'events', '事件', '活动', '里程碑', 'milestone']):
        if 'event' in file_types:
            return 'event'
    
    # 检测activity类型
    if any(keyword in filename_lower for keyword in ['activity', 'activities', 'daily', '日志', '记录', 'log']):
        if 'activity' in file_types:
            return 'activity'
    
    # 如果没有匹配，返回第一个可用类型
    return file_types[0]

def get_required_files() -> List[str]:
    """获取必须的文件类型列表"""
    manager = get_config_manager()
    return manager.get_all_file_types()

def get_optional_files() -> List[str]:
    """获取可选的文件类型列表（目前为空）"""
    return []

def get_simple_summary() -> Dict[str, Any]:
    """获取配置摘要"""
    manager = get_config_manager()
    file_types = manager.get_all_file_types()
    
    required_files = {}
    for file_type in file_types:
        config = manager.get_file_config(file_type)
        if config:
            required_files[file_type] = {
                "filename": config.filename,
                "description": config.description,
                "folder": config.folder_path
            }
    
    return {
        "required_files": required_files,
        "optional_files": {},
        "total_files": len(file_types),
        "processing_principle": f"动态加载{len(file_types)}个文件夹配置"
    }

def get_all_file_configs() -> Dict[str, MarkdownFileConfig]:
    """获取所有文件配置"""
    manager = get_config_manager()
    return {
        file_type: manager.get_file_config(file_type)
        for file_type in manager.get_all_file_types()
    } 