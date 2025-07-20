"""
Profile类型的配置文件
记录角色的个人信息、特征、喜好、背景等
"""

from dataclasses import dataclass

@dataclass
class ProfileConfig:
    """Profile文件的配置"""
    
    # 基本信息
    name: str = "profile"
    filename: str = "profile.md"
    description: str = "记录角色的个人信息、特征和喜好"
    
    # 文件夹路径
    folder_name: str = "profile"
    prompt_file: str = "prompt.txt"
    config_file: str = "config.py"

# 创建配置实例
CONFIG = ProfileConfig()

def get_config():
    """获取profile配置"""
    return CONFIG

def get_file_info():
    """获取文件信息"""
    return {
        "name": CONFIG.name,
        "filename": CONFIG.filename,
        "description": CONFIG.description,
        "folder": CONFIG.folder_name
    } 