"""
文献管理Agent - 主程序入口
功能：扫描PDF -> 解析内容 -> LLM分类 -> 自动归档 -> 构建知识图谱
"""
import sys
import argparse
from pathlib import Path
from typing import List, Optional

from config import PDF_SOURCE_DIR, OUTPUT_DIR, OPENAI_API_KEY
from scanner import scan_pdfs, get_pdf_info
from parser import parse_pdf
from classifier import LiteratureClassifier
from organizer import FileOrganizer
from database import LiteratureDatabase
from knowledge_graph import KnowledgeGraph


class LiteratureAgent:
    """文献管理智能代理"""
    
    def __init__(self):
        self.db = LiteratureDatabase()
        self.classifier = LiteratureClassifier()
        self.organizer = FileOrganizer()
        self.kg = KnowledgeGraph()
    
    def process_all(self, source_dir: Path = None, copy_files: bool = True):
        """
        处理所有PDF文献
        
        Args:
            source_dir: PDF源目录
            copy_files: True=复制到分类目录，False=移动
        """
        source_dir = source_dir or PDF_SOURCE_DIR
        
        print("="*60)
        print("📚 文献管理Agent 启动")
        print("="*60)
        
        # 检查API配置
        if not OPENAI_API_KEY or len(OPENAI_API_KEY) < 10 or OPENAI_API_KEY == "your-api-key-here":
            print("\n⚠️  警告: 请先在config.py中配置OPENAI_API_KEY")
            print("   或设置环境变量: set OPENAI_API_KEY=your-key")
            return
        
        print(f"✓ API已配置 (Key: {OPENAI_API_KEY[:8]}...)")
        
        # 1. 扫描PDF
        print(f"\n📂 扫描目录: {source_dir}")
        pdfs = scan_pdfs(source_dir)
        
        if not pdfs:
            print("未发现PDF文件，请将文献放入 '文献' 文件夹")
            return
        
        # 2. 逐个处理
        total = len(pdfs)
        success_count = 0
        
        for i, pdf_path in enumerate(pdfs):
            print(f"\n{'─'*50}")
            print(f"[{i+1}/{total}] 处理: {pdf_path.name}")
            
            try:
                # 解析PDF
                print("  → 解析PDF...")
                metadata = parse_pdf(pdf_path)
                
                if metadata.get("error"):
                    print(f"  ✗ 解析失败: {metadata['error']}")
                    continue
                
                print(f"  → 标题: {metadata.get('title', '未知')[:50]}...")
                print(f"  → 作者: {', '.join(metadata.get('authors', [])[:3]) or '未知'}")
                
                # LLM分类
                print("  → LLM分类中...")
                classification = self.classifier.classify(
                    title=metadata.get("title", ""),
                    abstract=metadata.get("abstract", ""),
                    keywords=metadata.get("keywords", [])
                )
                
                print(f"  → 学科: {classification.get('discipline', '未知')}")
                print(f"  → 类型: {classification.get('paper_type', '未知')}")
                print(f"  → 置信度: {classification.get('confidence', 0):.0%}")
                
                # 保存到数据库
                paper_id = self.db.add_paper(metadata, classification)
                print(f"  → 已存入数据库 (ID: {paper_id})")
                
                # 归档文件
                target = self.organizer.organize(
                    pdf_path,
                    classification.get("discipline", "其他"),
                    classification.get("sub_field"),
                    copy=copy_files
                )
                
                if target:
                    # 更新分类后路径
                    metadata["classified_path"] = str(target)
                    self.db.add_paper(metadata, classification)
                    print(f"  ✓ 已归档到: {target.parent.name}/{target.name}")
                
                success_count += 1
                
            except Exception as e:
                print(f"  ✗ 处理失败: {e}")
                continue
        
        # 3. 构建知识图谱
        print(f"\n{'─'*50}")
        print("🔗 构建知识图谱...")
        self.kg.build_from_database()
        graph_path = self.kg.visualize()
        
        # 4. 输出统计
        self._print_summary(success_count, total, graph_path)
    
    def process_single(self, pdf_path: Path, copy_file: bool = True):
        """处理单个PDF文件"""
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            print(f"文件不存在: {pdf_path}")
            return None
        
        print(f"处理文件: {pdf_path.name}")
        
        # 解析
        metadata = parse_pdf(pdf_path)
        
        # 分类
        classification = self.classifier.classify(
            title=metadata.get("title", ""),
            abstract=metadata.get("abstract", ""),
            keywords=metadata.get("keywords", [])
        )
        
        # 保存
        paper_id = self.db.add_paper(metadata, classification)
        
        # 归档
        target = self.organizer.organize(
            pdf_path,
            classification.get("discipline", "其他"),
            classification.get("sub_field"),
            copy=copy_file
        )
        
        return {
            "paper_id": paper_id,
            "metadata": metadata,
            "classification": classification,
            "target_path": str(target) if target else None
        }
    
    def build_graph_only(self):
        """仅构建知识图谱（使用已有数据）"""
        print("🔗 从数据库构建知识图谱...")
        self.kg.build_from_database()
        graph_path = self.kg.visualize()
        print(f"✓ 图谱已保存: {graph_path}")
        return graph_path
    
    def show_statistics(self):
        """显示统计信息"""
        stats = self.db.get_statistics()
        
        print("\n" + "="*50)
        print("📊 文献库统计")
        print("="*50)
        print(f"  总文献数: {stats['total_papers']}")
        print(f"  总作者数: {stats['total_authors']}")
        print("\n  学科分布:")
        for disc, count in stats['by_discipline'].items():
            print(f"    • {disc}: {count} 篇")
        print("="*50)
    
    def _print_summary(self, success: int, total: int, graph_path: Path):
        """打印处理摘要"""
        print("\n" + "="*60)
        print("✅ 处理完成")
        print("="*60)
        print(f"  成功处理: {success}/{total} 篇文献")
        print(f"  知识图谱: {graph_path}")
        print(f"  数据库:   {self.db.db_path}")
        
        # 显示分类统计
        self.organizer.print_statistics()
        
        print("\n💡 提示: 在浏览器中打开知识图谱HTML查看交互式可视化")
        print("="*60)


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="文献管理Agent - 自动分类与知识图谱构建"
    )
    parser.add_argument(
        "--source", "-s",
        type=str,
        default=None,
        help="PDF文献源目录"
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        default=None,
        help="处理单个PDF文件"
    )
    parser.add_argument(
        "--move",
        action="store_true",
        help="移动文件（默认是复制）"
    )
    parser.add_argument(
        "--graph-only",
        action="store_true",
        help="仅构建知识图谱（不处理新文献）"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="显示统计信息"
    )
    
    args = parser.parse_args()
    
    agent = LiteratureAgent()
    
    if args.stats:
        agent.show_statistics()
    elif args.graph_only:
        agent.build_graph_only()
    elif args.file:
        result = agent.process_single(Path(args.file), copy_file=not args.move)
        if result:
            print(f"\n分类结果: {result['classification']}")
    else:
        source = Path(args.source) if args.source else None
        agent.process_all(source, copy_files=not args.move)


if __name__ == "__main__":
    main()
