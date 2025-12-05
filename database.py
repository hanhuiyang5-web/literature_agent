"""
数据库模块
使用SQLite存储文献元数据和分类信息
"""
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from config import DATABASE_PATH, OUTPUT_DIR


class LiteratureDatabase:
    """文献数据库管理器"""
    
    def __init__(self, db_path: Path = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            from config import DATABASE_PATH
            self.db_path = DATABASE_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 文献主表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,
                    title TEXT,
                    authors TEXT,  -- JSON数组
                    abstract TEXT,
                    keywords TEXT,  -- JSON数组
                    page_count INTEGER,
                    discipline TEXT,
                    sub_field TEXT,
                    paper_type TEXT,
                    confidence REAL,
                    summary TEXT,
                    classified_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 引用关系表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS citations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_paper_id INTEGER,
                    to_paper_id INTEGER,
                    citation_text TEXT,
                    FOREIGN KEY (from_paper_id) REFERENCES papers(id),
                    FOREIGN KEY (to_paper_id) REFERENCES papers(id)
                )
            """)
            
            # 相似度关系表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS similarities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper1_id INTEGER,
                    paper2_id INTEGER,
                    similarity_score REAL,
                    FOREIGN KEY (paper1_id) REFERENCES papers(id),
                    FOREIGN KEY (paper2_id) REFERENCES papers(id)
                )
            """)
            
            # 作者表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS authors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            """)
            
            # 论文-作者关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_authors (
                    paper_id INTEGER,
                    author_id INTEGER,
                    PRIMARY KEY (paper_id, author_id),
                    FOREIGN KEY (paper_id) REFERENCES papers(id),
                    FOREIGN KEY (author_id) REFERENCES authors(id)
                )
            """)
            
            conn.commit()
            print(f"[数据库] 初始化完成: {self.db_path}")
    
    def add_paper(self, metadata: Dict, classification: Dict = None) -> int:
        """
        添加或更新文献记录
        
        Returns:
            paper_id
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 检查是否已存在
            cursor.execute(
                "SELECT id FROM papers WHERE file_path = ?",
                (metadata.get("file_path", ""),)
            )
            existing = cursor.fetchone()
            
            authors_json = json.dumps(metadata.get("authors", []), ensure_ascii=False)
            keywords_json = json.dumps(metadata.get("keywords", []), ensure_ascii=False)
            
            if existing:
                # 更新
                paper_id = existing[0]
                cursor.execute("""
                    UPDATE papers SET
                        title = ?, authors = ?, abstract = ?, keywords = ?,
                        page_count = ?, discipline = ?, sub_field = ?,
                        paper_type = ?, confidence = ?, summary = ?,
                        classified_path = ?, updated_at = ?
                    WHERE id = ?
                """, (
                    metadata.get("title", ""),
                    authors_json,
                    metadata.get("abstract", ""),
                    keywords_json,
                    metadata.get("page_count", 0),
                    classification.get("discipline", "") if classification else "",
                    classification.get("sub_field", "") if classification else "",
                    classification.get("paper_type", "") if classification else "",
                    classification.get("confidence", 0) if classification else 0,
                    classification.get("summary", "") if classification else "",
                    metadata.get("classified_path", ""),
                    datetime.now(),
                    paper_id
                ))
            else:
                # 插入
                cursor.execute("""
                    INSERT INTO papers (
                        file_path, filename, title, authors, abstract, keywords,
                        page_count, discipline, sub_field, paper_type, 
                        confidence, summary, classified_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metadata.get("file_path", ""),
                    metadata.get("filename", ""),
                    metadata.get("title", ""),
                    authors_json,
                    metadata.get("abstract", ""),
                    keywords_json,
                    metadata.get("page_count", 0),
                    classification.get("discipline", "") if classification else "",
                    classification.get("sub_field", "") if classification else "",
                    classification.get("paper_type", "") if classification else "",
                    classification.get("confidence", 0) if classification else 0,
                    classification.get("summary", "") if classification else "",
                    metadata.get("classified_path", "")
                ))
                paper_id = cursor.lastrowid
            
            # 处理作者关联
            self._update_authors(cursor, paper_id, metadata.get("authors", []))
            
            conn.commit()
            return paper_id
    
    def _update_authors(self, cursor, paper_id: int, authors: List[str]):
        """更新作者关联"""
        # 清除旧关联
        cursor.execute("DELETE FROM paper_authors WHERE paper_id = ?", (paper_id,))
        
        for author_name in authors:
            if not author_name.strip():
                continue
            
            # 获取或创建作者
            cursor.execute(
                "INSERT OR IGNORE INTO authors (name) VALUES (?)",
                (author_name.strip(),)
            )
            cursor.execute(
                "SELECT id FROM authors WHERE name = ?",
                (author_name.strip(),)
            )
            author_id = cursor.fetchone()[0]
            
            # 创建关联
            cursor.execute(
                "INSERT OR IGNORE INTO paper_authors (paper_id, author_id) VALUES (?, ?)",
                (paper_id, author_id)
            )
    
    def add_similarity(self, paper1_id: int, paper2_id: int, score: float):
        """添加相似度关系"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO similarities (paper1_id, paper2_id, similarity_score)
                VALUES (?, ?, ?)
            """, (paper1_id, paper2_id, score))
            conn.commit()
    
    def get_all_papers(self) -> List[Dict]:
        """获取所有文献"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM papers ORDER BY created_at DESC")
            rows = cursor.fetchall()
            
            papers = []
            for row in rows:
                paper = dict(row)
                paper["authors"] = json.loads(paper["authors"]) if paper["authors"] else []
                paper["keywords"] = json.loads(paper["keywords"]) if paper["keywords"] else []
                papers.append(paper)
            
            return papers
    
    def get_paper_by_id(self, paper_id: int) -> Optional[Dict]:
        """根据ID获取文献"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM papers WHERE id = ?", (paper_id,))
            row = cursor.fetchone()
            
            if row:
                paper = dict(row)
                paper["authors"] = json.loads(paper["authors"]) if paper["authors"] else []
                paper["keywords"] = json.loads(paper["keywords"]) if paper["keywords"] else []
                return paper
            return None
    
    def update_notes(self, paper_id: int, notes: str):
        """更新文献批注"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 检查notes列是否存在
            cursor.execute("PRAGMA table_info(papers)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'notes' not in columns:
                cursor.execute("ALTER TABLE papers ADD COLUMN notes TEXT")
            cursor.execute("UPDATE papers SET notes = ? WHERE id = ?", (notes, paper_id))
            conn.commit()
    
    def get_papers_by_discipline(self, discipline: str) -> List[Dict]:
        """根据学科获取文献"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM papers WHERE discipline = ? ORDER BY created_at DESC",
                (discipline,)
            )
            rows = cursor.fetchall()
            
            papers = []
            for row in rows:
                paper = dict(row)
                paper["authors"] = json.loads(paper["authors"]) if paper["authors"] else []
                paper["keywords"] = json.loads(paper["keywords"]) if paper["keywords"] else []
                papers.append(paper)
            
            return papers
    
    def get_all_authors(self) -> List[Dict]:
        """获取所有作者及其论文数"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.id, a.name, COUNT(pa.paper_id) as paper_count
                FROM authors a
                LEFT JOIN paper_authors pa ON a.id = pa.author_id
                GROUP BY a.id
                ORDER BY paper_count DESC
            """)
            return [{"id": r[0], "name": r[1], "paper_count": r[2]} for r in cursor.fetchall()]
    
    def get_similarities(self, threshold: float = 0.5) -> List[Dict]:
        """获取相似度关系"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT paper1_id, paper2_id, similarity_score
                FROM similarities
                WHERE similarity_score >= ?
            """, (threshold,))
            return [
                {"paper1_id": r[0], "paper2_id": r[1], "score": r[2]}
                for r in cursor.fetchall()
            ]
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 总文献数
            cursor.execute("SELECT COUNT(*) FROM papers")
            total_papers = cursor.fetchone()[0]
            
            # 各学科数量
            cursor.execute("""
                SELECT discipline, COUNT(*) as count
                FROM papers
                WHERE discipline != ''
                GROUP BY discipline
                ORDER BY count DESC
            """)
            by_discipline = {r[0]: r[1] for r in cursor.fetchall()}
            
            # 作者数
            cursor.execute("SELECT COUNT(*) FROM authors")
            total_authors = cursor.fetchone()[0]
            
            return {
                "total_papers": total_papers,
                "total_authors": total_authors,
                "by_discipline": by_discipline
            }


# 便捷函数
def save_to_db(metadata: Dict, classification: Dict = None) -> int:
    """保存文献到数据库"""
    db = LiteratureDatabase()
    return db.add_paper(metadata, classification)


def get_db() -> LiteratureDatabase:
    """获取数据库实例"""
    return LiteratureDatabase()


if __name__ == "__main__":
    # 测试数据库
    db = LiteratureDatabase()
    stats = db.get_statistics()
    print(f"数据库统计: {stats}")
