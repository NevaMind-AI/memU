"""
Activity类型的配置文件
每个md文件类型都有自己的文件夹和配置
"""

from dataclasses import dataclass

@dataclass
class ActivityConfig:
    """Activity文件的配置"""
    
    # 基本信息
    name: str = "activity"
    filename: str = "activity.md"
    description: str = "记录所有对话和活动内容"
    
    # 文件夹路径
    folder_name: str = "activity"
    prompt_file: str = "prompt.txt"
    config_file: str = "config.py"
    
    # RAG配置
    context: str = "rag"  # "all" 表示整体放入context，"rag" 表示只使用RAG搜索
    rag_length: int = 50  # RAG长度，-1表示全部，其他数值表示行数

# 创建配置实例
CONFIG = ActivityConfig()

def get_config():
    """获取activity配置"""
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