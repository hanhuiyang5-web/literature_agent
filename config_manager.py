"""
配置管理器 - 支持动态配置和持久化
"""
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict, field

CONFIG_FILE = Path(__file__).parent / "user_config.json"

@dataclass
class AppConfig:
    """应用配置"""
    # API配置
    api_key: str = ""
    api_base_url: str = "https://api.deepseek.com"
    model_name: str = "deepseek-chat"
    
    # 路径配置
    input_folder: str = ""
    output_folder: str = ""
    
    # 解析配置
    max_abstract_length: int = 2000
    max_pages_to_parse: int = 5
    similarity_threshold: float = 0.6
    
    # 学科分类
    disciplines: list = field(default_factory=lambda: [
        "计算机科学", "人工智能", "数学", "物理学", "化学",
        "生物学", "医学", "经济学", "管理学", "心理学",
        "社会学", "法学", "文学", "历史学", "地理学",
        "环境科学", "材料科学", "电子工程", "机械工程",
        "交通运输", "建筑学", "农学", "其他"
    ])
    
    @property
    def pdf_source_dir(self) -> Path:
        return Path(self.input_folder) if self.input_folder else None
    
    @property
    def classified_dir(self) -> Path:
        return Path(self.output_folder) / "文献_分类" if self.output_folder else None
    
    @property
    def database_path(self) -> Path:
        return Path(self.output_folder) / "literature.db" if self.output_folder else None
    
    @property
    def graph_output(self) -> Path:
        return Path(self.output_folder) / "knowledge_graph.html" if self.output_folder else None
    
    def is_configured(self) -> bool:
        return bool(self.api_key and self.input_folder and self.output_folder)
    
    def validate(self) -> tuple:
        if not self.api_key:
            return False, "请配置API Key"
        if not self.input_folder:
            return False, "请设置输入文件夹"
        if not Path(self.input_folder).exists():
            return False, f"输入文件夹不存在: {self.input_folder}"
        if not self.output_folder:
            return False, "请设置输出文件夹"
        return True, "配置有效"


def load_config() -> AppConfig:
    """加载配置"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return AppConfig(**data)
        except:
            pass
    return AppConfig()


def save_config(config: AppConfig):
    """保存配置"""
    data = asdict(config)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
