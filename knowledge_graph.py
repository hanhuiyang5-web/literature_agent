"""
知识图谱模块
构建文献之间的关系图谱并可视化
包括：引用关系、主题相似度、作者合作网络
"""
import json
import networkx as nx
from pyvis.network import Network
from pathlib import Path
from typing import Dict, List, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from config import GRAPH_OUTPUT, OUTPUT_DIR, SIMILARITY_THRESHOLD
from database import LiteratureDatabase


class KnowledgeGraph:
    """文献知识图谱构建器"""
    
    def __init__(self):
        self.G = nx.DiGraph()
        self.db = LiteratureDatabase()
        
        # 节点颜色配置
        self.colors = {
            "paper": "#97c2fc",       # 论文-蓝色
            "author": "#ffcc00",      # 作者-黄色
            "discipline": "#fb7e81",  # 学科-红色
            "keyword": "#7be141",     # 关键词-绿色
        }
        
        # 学科颜色映射
        self.discipline_colors = {}
    
    def build_from_database(self):
        """从数据库构建完整知识图谱"""
        papers = self.db.get_all_papers()
        
        if not papers:
            print("[图谱] 数据库中没有文献记录")
            return
        
        print(f"[图谱] 正在构建知识图谱，共 {len(papers)} 篇文献...")
        
        # 1. 添加所有论文节点
        for paper in papers:
            self.add_paper_node(paper)
        
        # 2. 添加作者节点和关系
        self._build_author_network(papers)
        
        # 3. 计算并添加相似度关系
        self._build_similarity_network(papers)
        
        # 4. 添加学科聚类
        self._build_discipline_clusters(papers)
        
        print(f"[图谱] 构建完成: {self.G.number_of_nodes()} 节点, {self.G.number_of_edges()} 边")
    
    def add_paper_node(self, paper: Dict):
        """添加论文节点"""
        paper_id = f"paper_{paper['id']}"
        
        # 获取学科颜色
        discipline = paper.get("discipline", "其他")
        color = self._get_discipline_color(discipline)
        
        self.G.add_node(
            paper_id,
            label=self._truncate(paper.get("title", "未知"), 40),
            title=self._build_paper_tooltip(paper),
            node_type="paper",
            discipline=discipline,
            color=color,
            size=25,
            shape="dot"
        )
    
    def _build_paper_tooltip(self, paper: Dict) -> str:
        """构建论文悬浮提示"""
        authors = ", ".join(paper.get("authors", [])[:3])
        if len(paper.get("authors", [])) > 3:
            authors += " 等"
        
        return f"""
        <b>{paper.get('title', '未知')}</b><br>
        <b>作者:</b> {authors or '未知'}<br>
        <b>学科:</b> {paper.get('discipline', '未知')}<br>
        <b>类型:</b> {paper.get('paper_type', '未知')}<br>
        <b>摘要:</b> {self._truncate(paper.get('summary', paper.get('abstract', '')), 200)}
        """
    
    def _build_author_network(self, papers: List[Dict]):
        """构建作者合作网络"""
        # 收集作者-论文关系
        author_papers = {}  # author -> [paper_ids]
        
        for paper in papers:
            paper_id = f"paper_{paper['id']}"
            authors = paper.get("authors", [])
            
            for author in authors:
                if not author.strip():
                    continue
                
                author_id = f"author_{author}"
                
                # 添加作者节点
                if author_id not in self.G:
                    self.G.add_node(
                        author_id,
                        label=author,
                        title=f"作者: {author}",
                        node_type="author",
                        color=self.colors["author"],
                        size=20,
                        shape="diamond"
                    )
                
                # 添加作者-论文边
                self.G.add_edge(
                    author_id, paper_id,
                    relation="authored",
                    color="#cccccc",
                    width=1
                )
                
                # 记录作者的论文
                if author not in author_papers:
                    author_papers[author] = []
                author_papers[author].append(paper_id)
        
        # 添加合作关系（同一论文的作者互相连接）
        for paper in papers:
            authors = paper.get("authors", [])
            if len(authors) > 1:
                for i in range(len(authors)):
                    for j in range(i + 1, len(authors)):
                        a1 = f"author_{authors[i]}"
                        a2 = f"author_{authors[j]}"
                        if a1 in self.G and a2 in self.G:
                            if not self.G.has_edge(a1, a2):
                                self.G.add_edge(
                                    a1, a2,
                                    relation="collaborates",
                                    color="#ffcc00",
                                    width=2,
                                    dashes=True
                                )
    
    def _build_similarity_network(self, papers: List[Dict]):
        """基于TF-IDF计算论文相似度"""
        if len(papers) < 2:
            return
        
        print("[图谱] 计算文献相似度...")
        
        # 构建文本语料
        texts = []
        valid_papers = []
        
        for paper in papers:
            text = " ".join([
                paper.get("title", ""),
                paper.get("abstract", ""),
                " ".join(paper.get("keywords", []))
            ])
            if text.strip():
                texts.append(text)
                valid_papers.append(paper)
        
        if len(texts) < 2:
            return
        
        # TF-IDF向量化
        try:
            vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            tfidf_matrix = vectorizer.fit_transform(texts)
            
            # 计算余弦相似度
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            # 添加相似度边（高于阈值的）
            for i in range(len(valid_papers)):
                for j in range(i + 1, len(valid_papers)):
                    sim_score = similarity_matrix[i][j]
                    
                    if sim_score >= SIMILARITY_THRESHOLD:
                        p1_id = f"paper_{valid_papers[i]['id']}"
                        p2_id = f"paper_{valid_papers[j]['id']}"
                        
                        self.G.add_edge(
                            p1_id, p2_id,
                            relation="similar",
                            similarity=round(sim_score, 3),
                            color="#97c2fc",
                            width=max(1, sim_score * 5),
                            title=f"相似度: {sim_score:.2%}"
                        )
                        
                        # 保存到数据库
                        self.db.add_similarity(
                            valid_papers[i]['id'],
                            valid_papers[j]['id'],
                            sim_score
                        )
            
            print(f"[图谱] 相似度计算完成")
            
        except Exception as e:
            print(f"[警告] 相似度计算失败: {e}")
    
    def _build_discipline_clusters(self, papers: List[Dict]):
        """构建学科聚类节点"""
        disciplines = {}
        
        for paper in papers:
            disc = paper.get("discipline", "其他")
            if disc not in disciplines:
                disciplines[disc] = []
            disciplines[disc].append(f"paper_{paper['id']}")
        
        # 添加学科节点
        for discipline, paper_ids in disciplines.items():
            if len(paper_ids) > 0:
                disc_id = f"discipline_{discipline}"
                color = self._get_discipline_color(discipline)
                
                self.G.add_node(
                    disc_id,
                    label=f"【{discipline}】",
                    title=f"学科: {discipline}\n文献数: {len(paper_ids)}",
                    node_type="discipline",
                    color=color,
                    size=35,
                    shape="star",
                    font={"size": 16, "face": "Microsoft YaHei"}
                )
                
                # 连接学科到论文
                for paper_id in paper_ids:
                    self.G.add_edge(
                        disc_id, paper_id,
                        relation="contains",
                        color=color,
                        width=1,
                        dashes=[5, 5]
                    )
    
    def add_citation(self, from_paper_id: int, to_paper_id: int, citation_text: str = ""):
        """添加引用关系"""
        from_id = f"paper_{from_paper_id}"
        to_id = f"paper_{to_paper_id}"
        
        if from_id in self.G and to_id in self.G:
            self.G.add_edge(
                from_id, to_id,
                relation="cites",
                title=f"引用: {self._truncate(citation_text, 100)}",
                color="#ff6b6b",
                width=2,
                arrows="to"
            )
    
    def _get_discipline_color(self, discipline: str) -> str:
        """获取学科对应的颜色"""
        if discipline not in self.discipline_colors:
            # 预定义颜色列表
            color_palette = [
                "#97c2fc", "#ffcc00", "#fb7e81", "#7be141", "#ad85e4",
                "#6ee7b7", "#fcd34d", "#f87171", "#a78bfa", "#60a5fa",
                "#34d399", "#fbbf24", "#f472b6", "#818cf8", "#2dd4bf",
            ]
            idx = len(self.discipline_colors) % len(color_palette)
            self.discipline_colors[discipline] = color_palette[idx]
        
        return self.discipline_colors[discipline]
    
    def _truncate(self, text: str, max_len: int) -> str:
        """截断文本"""
        if not text:
            return ""
        text = str(text)
        return text[:max_len] + "..." if len(text) > max_len else text
    
    def visualize(self, output_path: Path = None, show_physics: bool = True):
        """
        生成交互式可视化图谱
        
        Args:
            output_path: 输出HTML文件路径
            show_physics: 是否启用物理引擎（节点自动布局）
        """
        if output_path is None:
            output_path = GRAPH_OUTPUT
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建pyvis网络
        net = Network(
            height="900px",
            width="100%",
            bgcolor="#ffffff",
            font_color="#333333",
            directed=True,
            notebook=False
        )
        
        # 物理引擎配置
        if show_physics:
            net.set_options("""
            {
                "physics": {
                    "enabled": true,
                    "barnesHut": {
                        "gravitationalConstant": -8000,
                        "centralGravity": 0.3,
                        "springLength": 150,
                        "springConstant": 0.04,
                        "damping": 0.09
                    },
                    "stabilization": {
                        "enabled": true,
                        "iterations": 1000
                    }
                },
                "interaction": {
                    "hover": true,
                    "tooltipDelay": 100,
                    "navigationButtons": true,
                    "keyboard": true
                },
                "nodes": {
                    "font": {
                        "face": "Microsoft YaHei, Arial",
                        "size": 14
                    }
                },
                "edges": {
                    "smooth": {
                        "type": "continuous"
                    }
                }
            }
            """)
        
        # 添加节点
        for node, data in self.G.nodes(data=True):
            net.add_node(
                node,
                label=data.get("label", node),
                title=data.get("title", ""),
                color=data.get("color", "#97c2fc"),
                size=data.get("size", 20),
                shape=data.get("shape", "dot")
            )
        
        # 添加边
        for u, v, data in self.G.edges(data=True):
            net.add_edge(
                u, v,
                title=data.get("title", data.get("relation", "")),
                color=data.get("color", "#cccccc"),
                width=data.get("width", 1),
                dashes=data.get("dashes", False)
            )
        
        # 添加自定义HTML头部（图例）
        legend_html = self._generate_legend_html()
        
        # 保存
        net.save_graph(str(output_path))
        
        # 注入图例
        self._inject_legend(output_path, legend_html)
        
        print(f"[图谱] 可视化已保存: {output_path}")
        return output_path
    
    def _generate_legend_html(self) -> str:
        """生成图例HTML"""
        return """
        <div id="legend" style="position: fixed; top: 10px; left: 10px; background: white; 
             padding: 15px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
             font-family: 'Microsoft YaHei', Arial; font-size: 13px; z-index: 1000;">
            <div style="font-weight: bold; margin-bottom: 10px; font-size: 14px;">📚 文献知识图谱</div>
            <div style="margin: 5px 0;"><span style="display: inline-block; width: 12px; height: 12px; 
                 background: #97c2fc; border-radius: 50%; margin-right: 8px;"></span>论文</div>
            <div style="margin: 5px 0;"><span style="display: inline-block; width: 12px; height: 12px; 
                 background: #ffcc00; transform: rotate(45deg); margin-right: 8px;"></span>作者</div>
            <div style="margin: 5px 0;"><span style="display: inline-block; width: 12px; height: 12px; 
                 background: #fb7e81; clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%); 
                 margin-right: 8px;"></span>学科</div>
            <hr style="margin: 10px 0; border: none; border-top: 1px solid #eee;">
            <div style="font-size: 12px; color: #666;">
                <div>实线: 相似关系</div>
                <div>虚线: 学科归属</div>
                <div>菱形: 作者-论文</div>
            </div>
        </div>
        """
    
    def _inject_legend(self, html_path: Path, legend_html: str):
        """将图例注入HTML文件"""
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 在body结束前注入
            content = content.replace('</body>', f'{legend_html}</body>')
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"[警告] 注入图例失败: {e}")
    
    def get_statistics(self) -> Dict:
        """获取图谱统计信息"""
        node_types = {}
        for _, data in self.G.nodes(data=True):
            t = data.get("node_type", "unknown")
            node_types[t] = node_types.get(t, 0) + 1
        
        edge_types = {}
        for _, _, data in self.G.edges(data=True):
            r = data.get("relation", "unknown")
            edge_types[r] = edge_types.get(r, 0) + 1
        
        return {
            "total_nodes": self.G.number_of_nodes(),
            "total_edges": self.G.number_of_edges(),
            "node_types": node_types,
            "edge_types": edge_types
        }


def build_knowledge_graph() -> Path:
    """
    便捷函数：构建并可视化知识图谱
    """
    kg = KnowledgeGraph()
    kg.build_from_database()
    return kg.visualize()


if __name__ == "__main__":
    # 测试知识图谱
    output = build_knowledge_graph()
    print(f"知识图谱已生成: {output}")
