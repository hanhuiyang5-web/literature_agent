"""
文件组织模块
自动创建分类文件夹并归档文献
"""
import shutil
from pathlib import Path
from typing import Optional
from config import CLASSIFIED_DIR, DISCIPLINES


class FileOrganizer:
    """文献文件组织器"""
    
    def __init__(self, base_dir: Path = None):
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            from config import CLASSIFIED_DIR
            self.base_dir = CLASSIFIED_DIR
        self._ensure_directories()
    
    def _ensure_directories(self):
        """仅创建基础分类目录（学科文件夹按需创建）"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        print(f"[组织] 分类目录: {self.base_dir}")
    
    def organize(self, source_path: Path, discipline: str, 
                 sub_field: str = None, copy: bool = True) -> Optional[Path]:
        """
        将文献归档到对应学科文件夹
        
        Args:
            source_path: 源PDF文件路径
            discipline: 学科分类
            sub_field: 细分领域（可选，会创建子文件夹）
            copy: True=复制，False=移动
        
        Returns:
            目标路径，失败返回None
        """
        source_path = Path(source_path)
        
        if not source_path.exists():
            print(f"[错误] 源文件不存在: {source_path}")
            return None
        
        # 确定目标目录
        if discipline not in DISCIPLINES:
            discipline = "其他"
        
        target_dir = self.base_dir / discipline
        target_dir.mkdir(exist_ok=True)  # 按需创建学科目录
        
        # 如果有细分领域，创建子目录
        if sub_field:
            # 清理子目录名（去除非法字符）
            sub_field_clean = self._clean_dirname(sub_field)
            if sub_field_clean:
                target_dir = target_dir / sub_field_clean
                target_dir.mkdir(exist_ok=True)
        
        # 目标文件路径
        target_path = target_dir / source_path.name
        
        # 处理重名
        if target_path.exists():
            target_path = self._get_unique_path(target_path)
        
        try:
            if copy:
                shutil.copy2(source_path, target_path)
                print(f"[复制] {source_path.name} -> {discipline}/{sub_field or ''}")
            else:
                shutil.move(source_path, target_path)
                print(f"[移动] {source_path.name} -> {discipline}/{sub_field or ''}")
            
            return target_path
            
        except Exception as e:
            print(f"[错误] 文件操作失败: {e}")
            return None
    
    def _clean_dirname(self, name: str) -> str:
        """清理目录名，去除非法字符"""
        # Windows非法字符
        illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in illegal_chars:
            name = name.replace(char, '_')
        return name.strip()[:50]  # 限制长度
    
    def _get_unique_path(self, path: Path) -> Path:
        """获取唯一的文件路径（避免重名）"""
        counter = 1
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        
        while path.exists():
            path = parent / f"{stem}_{counter}{suffix}"
            counter += 1
        
        return path
    
    def get_statistics(self) -> dict:
        """获取分类统计信息"""
        stats = {}
        
        for discipline in DISCIPLINES:
            discipline_dir = self.base_dir / discipline
            if discipline_dir.exists():
                pdf_count = len(list(discipline_dir.rglob("*.pdf")))
                if pdf_count > 0:
                    stats[discipline] = pdf_count
        
        return stats
    
    def print_statistics(self):
        """打印分类统计"""
        stats = self.get_statistics()
        
        print("\n" + "="*50)
        print("文献分类统计")
        print("="*50)
        
        total = 0
        for discipline, count in sorted(stats.items(), key=lambda x: -x[1]):
            print(f"  {discipline}: {count} 篇")
            total += count
        
        print("-"*50)
        print(f"  总计: {total} 篇")
        print("="*50)


def organize_file(source_path: Path, discipline: str, 
                  sub_field: str = None, copy: bool = True) -> Optional[Path]:
    """
    便捷函数：归档单个文件
    """
    organizer = FileOrganizer()
    return organizer.organize(source_path, discipline, sub_field, copy)


if __name__ == "__main__":
    # 测试组织器
    organizer = FileOrganizer()
    organizer.print_statistics()
