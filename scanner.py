"""
PDF文件扫描模块
递归扫描指定目录下的所有PDF文件
"""
import os
from pathlib import Path
from typing import List, Generator
def scan_pdfs(directory: Path = None, recursive: bool = True) -> List[Path]:
    """
    扫描目录下的所有PDF文件
    
    Args:
        directory: 扫描目录
        recursive: 是否递归扫描子目录
    
    Returns:
        PDF文件路径列表
    """
    if directory is None:
        from config import PDF_SOURCE_DIR
        directory = PDF_SOURCE_DIR
    
    directory = Path(directory)
    
    if not directory.exists():
        print(f"[警告] 目录不存在: {directory}")
        return []
    
    pdf_files = []
    
    if recursive:
        for pdf_path in directory.rglob("*.pdf"):
            pdf_files.append(pdf_path)
    else:
        for pdf_path in directory.glob("*.pdf"):
            pdf_files.append(pdf_path)
    
    print(f"[扫描] 在 {directory} 中发现 {len(pdf_files)} 个PDF文件")
    return pdf_files


def scan_pdfs_generator(directory: Path = None) -> Generator[Path, None, None]:
    """
    生成器方式扫描PDF，适合大量文件
    """
    if directory is None:
        directory = PDF_SOURCE_DIR
    
    directory = Path(directory)
    
    for pdf_path in directory.rglob("*.pdf"):
        yield pdf_path


def get_pdf_info(pdf_path: Path) -> dict:
    """
    获取PDF文件基本信息
    """
    stat = pdf_path.stat()
    return {
        "path": str(pdf_path),
        "filename": pdf_path.name,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modified_time": stat.st_mtime,
    }


if __name__ == "__main__":
    # 测试扫描
    pdfs = scan_pdfs()
    for pdf in pdfs:
        info = get_pdf_info(pdf)
        print(f"  - {info['filename']} ({info['size_mb']} MB)")
