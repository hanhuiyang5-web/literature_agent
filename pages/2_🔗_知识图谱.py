"""
知识图谱页面 - 按学科分类展示
"""
import streamlit as st
from pathlib import Path
import sys
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).parent.parent))

from config_manager import load_config

st.markdown('<p class="main-title">🔗 知识图谱</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">可视化文献关系网络</p>', unsafe_allow_html=True)

# 加载配置
if 'config' not in st.session_state:
    st.session_state.config = load_config()

config = st.session_state.config

if not config.is_configured():
    st.warning("⚠️ 请先完成设置后再使用此功能")
    st.stop()

from database import LiteratureDatabase
from knowledge_graph import KnowledgeGraph

# 初始化
db = LiteratureDatabase(config.database_path)
stats = db.get_statistics()

# 顶部控制栏
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    # 学科筛选
    disciplines_with_count = ["全部学科"]
    for disc, count in stats.get('by_discipline', {}).items():
        disciplines_with_count.append(f"{disc} ({count})")
    
    selected = st.selectbox(
        "📂 选择学科",
        disciplines_with_count,
        label_visibility="collapsed"
    )
    
    # 解析选择的学科
    if selected == "全部学科":
        selected_discipline = None
    else:
        selected_discipline = selected.rsplit(' (', 1)[0]

with col2:
    # 关系类型筛选
    relation_types = st.multiselect(
        "关系类型",
        ["相似关系", "作者关系", "学科归属"],
        default=["相似关系", "作者关系", "学科归属"],
        label_visibility="collapsed"
    )

with col3:
    regenerate = st.button("🔄 重新生成", use_container_width=True)

st.markdown("---")

# 统计信息
col1, col2, col3, col4 = st.columns(4)

papers = db.get_all_papers()
if selected_discipline:
    papers = [p for p in papers if p.get('discipline') == selected_discipline]

with col1:
    st.metric("📄 文献数", len(papers))
with col2:
    authors = set()
    for p in papers:
        authors.update(p.get('authors', []))
    st.metric("👤 作者数", len(authors))
with col3:
    keywords = set()
    for p in papers:
        keywords.update(p.get('keywords', []))
    st.metric("🏷️ 关键词", len(keywords))
with col4:
    st.metric("🔗 相似对", len(db.get_similarities(config.similarity_threshold)))

st.markdown("---")

# 生成或加载图谱
def generate_filtered_graph(discipline: str = None, relations: list = None):
    """生成筛选后的知识图谱"""
    import networkx as nx
    from pyvis.network import Network
    
    kg = KnowledgeGraph()
    kg.db = db
    
    # 获取文献
    if discipline:
        papers = db.get_papers_by_discipline(discipline)
    else:
        papers = db.get_all_papers()
    
    if not papers:
        return None
    
    # 添加论文节点
    for paper in papers:
        paper_id = f"paper_{paper['id']}"
        kg.G.add_node(
            paper_id,
            label=paper.get('title', '未知')[:30] + "...",
            title=f"<b>{paper.get('title', '未知')}</b><br>学科: {paper.get('discipline', '未知')}<br>作者: {', '.join(paper.get('authors', [])[:3])}",
            color="#6366f1",
            size=25,
            shape="dot"
        )
    
    paper_ids = {f"paper_{p['id']}" for p in papers}
    
    # 添加作者关系
    if relations and "作者关系" in relations:
        for paper in papers:
            paper_id = f"paper_{paper['id']}"
            for author in paper.get('authors', [])[:5]:
                if author.strip():
                    author_id = f"author_{author}"
                    if author_id not in kg.G:
                        kg.G.add_node(
                            author_id,
                            label=author,
                            title=f"作者: {author}",
                            color="#f59e0b",
                            size=18,
                            shape="diamond"
                        )
                    kg.G.add_edge(author_id, paper_id, color="#d1d5db", width=1)
    
    # 添加相似关系
    if relations and "相似关系" in relations:
        similarities = db.get_similarities(config.similarity_threshold)
        for sim in similarities:
            p1 = f"paper_{sim['paper1_id']}"
            p2 = f"paper_{sim['paper2_id']}"
            if p1 in paper_ids and p2 in paper_ids:
                kg.G.add_edge(
                    p1, p2,
                    color="#10b981",
                    width=max(1, sim['score'] * 4),
                    title=f"相似度: {sim['score']:.0%}"
                )
    
    # 添加学科节点
    if relations and "学科归属" in relations:
        disc_papers = {}
        for paper in papers:
            d = paper.get('discipline', '其他')
            if d not in disc_papers:
                disc_papers[d] = []
            disc_papers[d].append(f"paper_{paper['id']}")
        
        for disc, pids in disc_papers.items():
            disc_id = f"disc_{disc}"
            kg.G.add_node(
                disc_id,
                label=f"【{disc}】",
                title=f"学科: {disc}<br>文献数: {len(pids)}",
                color="#ef4444",
                size=35,
                shape="star"
            )
            for pid in pids:
                kg.G.add_edge(disc_id, pid, color="#fecaca", width=1, dashes=True)
    
    # 生成HTML
    net = Network(
        height="600px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#333333",
        directed=False
    )
    
    net.set_options("""
    {
        "physics": {
            "enabled": true,
            "barnesHut": {
                "gravitationalConstant": -5000,
                "centralGravity": 0.3,
                "springLength": 120
            },
            "stabilization": {"iterations": 500}
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 100
        },
        "nodes": {
            "font": {"face": "Microsoft YaHei, Arial", "size": 12}
        }
    }
    """)
    
    for node, data in kg.G.nodes(data=True):
        net.add_node(
            node,
            label=data.get("label", node),
            title=data.get("title", ""),
            color=data.get("color", "#6366f1"),
            size=data.get("size", 20),
            shape=data.get("shape", "dot")
        )
    
    for u, v, data in kg.G.edges(data=True):
        net.add_edge(
            u, v,
            color=data.get("color", "#d1d5db"),
            width=data.get("width", 1),
            title=data.get("title", ""),
            dashes=data.get("dashes", False)
        )
    
    # 保存到临时文件
    output_path = config.graph_output.parent / f"graph_{'all' if not discipline else discipline}.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    net.save_graph(str(output_path))
    
    # 添加图例
    legend = """
    <div style="position:fixed;top:10px;left:10px;background:#fff;padding:15px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,0.1);font-size:13px;z-index:1000;">
        <div style="font-weight:600;margin-bottom:8px;">📊 图例</div>
        <div style="margin:4px 0;"><span style="display:inline-block;width:12px;height:12px;background:#6366f1;border-radius:50%;margin-right:8px;"></span>论文</div>
        <div style="margin:4px 0;"><span style="display:inline-block;width:12px;height:12px;background:#f59e0b;transform:rotate(45deg);margin-right:8px;"></span>作者</div>
        <div style="margin:4px 0;"><span style="display:inline-block;width:12px;height:12px;background:#ef4444;clip-path:polygon(50% 0%,100% 50%,50% 100%,0% 50%);margin-right:8px;"></span>学科</div>
        <hr style="margin:8px 0;border:none;border-top:1px solid #eee;">
        <div style="font-size:11px;color:#666;">绿线=相似 | 虚线=归属</div>
    </div>
    """
    
    with open(output_path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace('</body>', f'{legend}</body>')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return output_path

# 显示图谱
if regenerate or 'graph_html' not in st.session_state:
    with st.spinner("正在生成知识图谱..."):
        graph_path = generate_filtered_graph(selected_discipline, relation_types)
        if graph_path:
            st.session_state.graph_html = graph_path
        else:
            st.session_state.graph_html = None

if st.session_state.get('graph_html') and Path(st.session_state.graph_html).exists():
    # 嵌入HTML
    with open(st.session_state.graph_html, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    components.html(html_content, height=650, scrolling=True)
    
    # 下载按钮
    st.download_button(
        label="📥 下载图谱HTML",
        data=html_content,
        file_name="knowledge_graph.html",
        mime="text/html"
    )
else:
    st.info("暂无图谱数据，请先处理一些文献")

# 文献列表（当前学科）
if selected_discipline and papers:
    st.markdown("---")
    st.markdown(f"### 📚 {selected_discipline} 文献列表")
    
    for paper in papers[:10]:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"**{paper.get('title', '未知')[:60]}...**")
            st.caption(f"👤 {', '.join(paper.get('authors', [])[:2]) or '未知'}")
        with col2:
            st.caption(f"{paper.get('paper_type', '未知')}")
