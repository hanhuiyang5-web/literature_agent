"""
文献管理Agent配置文件
注意：此文件仅用于命令行模式。Streamlit应用使用 config_manager.py 动态管理配置。
"""
import os
from pathlib import Path

# ============== API配置 ==============
# 通过环境变量或在应用设置页面配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")

# ============== 路径配置 ==============
# 命令行模式的默认路径（Streamlit应用使用设置页面配置）
BASE_DIR = Path(__file__).parent.parent
PDF_SOURCE_DIR = BASE_DIR / "文献"              # PDF源文件夹
CLASSIFIED_DIR = BASE_DIR / "文献_分类"         # 分类后的文件夹
OUTPUT_DIR = BASE_DIR / "output"                # 输出目录
DATABASE_PATH = OUTPUT_DIR / "literature.db"    # 数据库路径
GRAPH_OUTPUT = OUTPUT_DIR / "knowledge_graph.html"  # 知识图谱输出

# ============== 学科分类 ==============
DISCIPLINES = [
    "计算机科学",
    "人工智能",
    "数学",
    "物理学",
    "化学",
    "生物学",
    "医学",
    "经济学",
    "管理学",
    "心理学",
    "社会学",
    "法学",
    "文学",
    "历史学",
    "地理学",
    "环境科学",
    "材料科学",
    "电子工程",
    "机械工程",
    "交通运输",
    "建筑学",
    "农学",
    "其他"
]

# ============== 解析配置 ==============
MAX_ABSTRACT_LENGTH = 2000      # 摘要最大字符数
MAX_PAGES_TO_PARSE = 5          # 解析前N页提取信息
SIMILARITY_THRESHOLD = 0.6      # 主题相似度阈值
