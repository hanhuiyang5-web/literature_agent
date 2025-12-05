"""
PDF解析模块
提取PDF的标题、作者、摘要、关键词、引用等信息
"""
import re
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Optional
from config import MAX_ABSTRACT_LENGTH, MAX_PAGES_TO_PARSE


class PDFParser:
    """PDF文献解析器"""
    
    def __init__(self, pdf_path: Path):
        self.pdf_path = Path(pdf_path)
        self.doc = None
        self.text_content = ""
        self.metadata = {}
    
    def __enter__(self):
        self.doc = fitz.open(self.pdf_path)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.doc:
            self.doc.close()
    
    def parse(self) -> Dict:
        """
        解析PDF，提取所有元数据
        """
        if not self.doc:
            self.doc = fitz.open(self.pdf_path)
        
        # 提取前N页文本
        self._extract_text()
        
        # 提取各项信息
        result = {
            "file_path": str(self.pdf_path),
            "filename": self.pdf_path.name,
            "title": self._extract_title(),
            "authors": self._extract_authors(),
            "abstract": self._extract_abstract(),
            "keywords": self._extract_keywords(),
            "references": self._extract_references(),
            "page_count": len(self.doc),
            "pdf_metadata": dict(self.doc.metadata) if self.doc.metadata else {},
        }
        
        return result
    
    def _extract_text(self) -> str:
        """提取前N页的文本内容"""
        pages_to_read = min(MAX_PAGES_TO_PARSE, len(self.doc))
        text_parts = []
        
        for page_num in range(pages_to_read):
            page = self.doc[page_num]
            text_parts.append(page.get_text())
        
        self.text_content = "\n".join(text_parts)
        return self.text_content
    
    def _extract_title(self) -> str:
        """提取标题"""
        # 优先从PDF元数据获取
        if self.doc.metadata and self.doc.metadata.get("title"):
            title = self.doc.metadata["title"].strip()
            if len(title) > 5:  # 有效标题
                return title
        
        # 从第一页提取（通常是最大字号的文本）
        if len(self.doc) > 0:
            first_page = self.doc[0]
            blocks = first_page.get_text("dict")["blocks"]
            
            # 找最大字号的文本块
            max_size = 0
            title_candidate = ""
            
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            if span["size"] > max_size and len(span["text"].strip()) > 5:
                                max_size = span["size"]
                                title_candidate = span["text"].strip()
            
            if title_candidate:
                return title_candidate
        
        # 回退：使用文件名
        return self.pdf_path.stem
    
    def _extract_authors(self) -> List[str]:
        """提取作者列表"""
        authors = []
        
        # 从PDF元数据获取
        if self.doc.metadata and self.doc.metadata.get("author"):
            author_str = self.doc.metadata["author"]
            # 分割多个作者
            for sep in [",", ";", "and", "&", "、"]:
                if sep in author_str:
                    authors = [a.strip() for a in author_str.split(sep) if a.strip()]
                    break
            if not authors:
                authors = [author_str.strip()]
        
        # 从文本中查找作者模式
        if not authors:
            # 常见的作者行模式
            author_patterns = [
                r"(?:Author[s]?|作者)[:\s]*([^\n]+)",
                r"(?:By|by)[:\s]*([^\n]+)",
            ]
            for pattern in author_patterns:
                match = re.search(pattern, self.text_content[:2000])
                if match:
                    author_str = match.group(1)
                    for sep in [",", ";", "and", "&", "、"]:
                        if sep in author_str:
                            authors = [a.strip() for a in author_str.split(sep) if a.strip()]
                            break
                    if not authors and author_str.strip():
                        authors = [author_str.strip()]
                    break
        
        return authors[:10]  # 最多返回10个作者
    
    def _extract_abstract(self) -> str:
        """提取摘要"""
        abstract = ""
        
        # 匹配Abstract/摘要部分
        patterns = [
            r"(?:Abstract|ABSTRACT|摘\s*要)[:\s]*\n?(.*?)(?:\n\s*(?:Keywords|KEYWORDS|关键词|Introduction|INTRODUCTION|1\.|1\s|引言)|$)",
            r"(?:Summary|SUMMARY)[:\s]*\n?(.*?)(?:\n\s*(?:Keywords|Introduction|1\.)|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text_content, re.DOTALL | re.IGNORECASE)
            if match:
                abstract = match.group(1).strip()
                # 清理多余空白
                abstract = re.sub(r'\s+', ' ', abstract)
                break
        
        # 截断过长摘要
        if len(abstract) > MAX_ABSTRACT_LENGTH:
            abstract = abstract[:MAX_ABSTRACT_LENGTH] + "..."
        
        return abstract
    
    def _extract_keywords(self) -> List[str]:
        """提取关键词"""
        keywords = []
        
        patterns = [
            r"(?:Keywords|KEYWORDS|关键词|Key\s*words)[:\s]*([^\n]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text_content, re.IGNORECASE)
            if match:
                kw_str = match.group(1)
                # 分割关键词
                for sep in [";", ",", "；", "，", "、"]:
                    if sep in kw_str:
                        keywords = [k.strip() for k in kw_str.split(sep) if k.strip()]
                        break
                break
        
        return keywords[:15]  # 最多15个关键词
    
    def _extract_references(self) -> List[str]:
        """提取参考文献列表"""
        references = []
        
        # 获取全文用于查找参考文献
        full_text = ""
        for page in self.doc:
            full_text += page.get_text()
        
        # 查找References部分
        ref_patterns = [
            r"(?:References|REFERENCES|参考文献)\s*\n(.*?)$",
            r"(?:Bibliography|BIBLIOGRAPHY)\s*\n(.*?)$",
        ]
        
        ref_section = ""
        for pattern in ref_patterns:
            match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
            if match:
                ref_section = match.group(1)
                break
        
        if ref_section:
            # 按编号分割参考文献
            # 匹配 [1], 1., (1) 等格式
            ref_items = re.split(r'\n\s*(?:\[\d+\]|\d+\.|\(\d+\))\s*', ref_section)
            references = [ref.strip().replace('\n', ' ') for ref in ref_items if len(ref.strip()) > 10]
        
        return references[:100]  # 最多100条引用
    
    def get_full_text(self) -> str:
        """获取完整文本（用于相似度计算）"""
        if not self.doc:
            self.doc = fitz.open(self.pdf_path)
        
        full_text = ""
        for page in self.doc:
            full_text += page.get_text()
        return full_text


def parse_pdf(pdf_path: Path) -> Dict:
    """
    解析单个PDF文件
    
    Args:
        pdf_path: PDF文件路径
    
    Returns:
        包含标题、作者、摘要等的字典
    """
    try:
        with PDFParser(pdf_path) as parser:
            return parser.parse()
    except Exception as e:
        print(f"[错误] 解析PDF失败 {pdf_path}: {e}")
        return {
            "file_path": str(pdf_path),
            "filename": Path(pdf_path).name,
            "title": Path(pdf_path).stem,
            "authors": [],
            "abstract": "",
            "keywords": [],
            "references": [],
            "page_count": 0,
            "pdf_metadata": {},
            "error": str(e)
        }


if __name__ == "__main__":
    # 测试解析
    from scanner import scan_pdfs
    
    pdfs = scan_pdfs()
    if pdfs:
        result = parse_pdf(pdfs[0])
        print(f"标题: {result['title']}")
        print(f"作者: {result['authors']}")
        print(f"摘要: {result['abstract'][:200]}...")
        print(f"关键词: {result['keywords']}")
        print(f"引用数: {len(result['references'])}")
