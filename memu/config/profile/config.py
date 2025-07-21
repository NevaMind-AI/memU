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
    
    # RAG配置
    context: str = "all"  # "all" 表示整体放入context，"rag" 表示只使用RAG搜索
    rag_length: int = -1  # RAG长度，-1表示全部，其他数值表示行数

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
        "folder": CONFIG.folder_name,
        "context": CONFIG.context,
        "rag_length": CONFIG.rag_length
    } 