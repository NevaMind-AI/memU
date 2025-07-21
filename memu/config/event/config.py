"""
Event类型的配置文件
记录重要事件、活动、里程碑等
"""

from dataclasses import dataclass

@dataclass
class EventConfig:
    """Event文件的配置"""
    
    # 基本信息
    name: str = "event"
    filename: str = "event.md"
    description: str = "记录重要事件、活动和里程碑"
    
    # 文件夹路径
    folder_name: str = "event"
    prompt_file: str = "prompt.txt"
    config_file: str = "config.py"
    
    # RAG配置
    context: str = "rag"  # "all" 表示整体放入context，"rag" 表示只使用RAG搜索
    rag_length: int = 30  # RAG长度，-1表示全部，其他数值表示行数

# 创建配置实例
CONFIG = EventConfig()

def get_config():
    """获取event配置"""
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