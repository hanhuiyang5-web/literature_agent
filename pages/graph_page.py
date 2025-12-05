"""
知识图谱页面 - 按学科分类展示
"""
import streamlit as st
from pathlib import Path
import sys
import streamlit.components.v1 as components
import networkx as nx
from pyvis.network import Network

sys.path.insert(0, str(Path(__file__).parent.parent))


def render(config):
    st.markdown("## 🔗 知识图谱")
    st.caption("可视化文献关系网络")
    
    if not config.is_configured():
        st.warning("⚠️ 请先完成设置后再使用此功能")
        return
    
    from database import LiteratureDatabase
    
    db = LiteratureDatabase(config.database_path)
    stats = db.get_statistics()
    
    # 控制栏
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        options = ["全部学科"]
        for disc, count in stats.get('by_discipline', {}).items():
            options.append(f"{disc} ({count})")
        
        selected = st.selectbox("📂 选择学科", options, label_visibility="collapsed")
        discipline = None if selected == "全部学科" else selected.rsplit(' (', 1)[0]
    
    with col2:
        relations = st.multiselect(
            "关系类型",
            ["相似关系", "作者关系", "学科归属"],
            default=["相似关系", "学科归属"],
            label_visibility="collapsed"
        )
    
    with col3:
        regenerate = st.button("🔄 刷新", use_container_width=True)
    
    st.markdown("---")
    
    # 统计
    papers = db.get_all_papers()
    if discipline:
        papers = [p for p in papers if p.get('discipline') == discipline]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📄 文献", len(papers))
    with col2:
        authors = set()
        for p in papers:
            authors.update(p.get('authors', []))
        st.metric("👤 作者", len(authors))
    with col3:
        kws = set()
        for p in papers:
            kws.update(p.get('keywords', []))
        st.metric("🏷️ 关键词", len(kws))
    with col4:
        st.metric("🔗 相似对", len(db.get_similarities(config.similarity_threshold)))
    
    st.markdown("---")
    
    # 生成图谱
    if not papers:
        st.info("暂无数据")
        return
    
    def build_graph():
        G = nx.Graph()
        
        # 论文节点
        for p in papers:
            pid = f"p_{p['id']}"
            G.add_node(pid, 
                label=p.get('title', '未知')[:25] + "...",
                title=f"<b>{p.get('title', '')}</b><br>学科: {p.get('discipline', '')}<br>作者: {', '.join(p.get('authors', [])[:2])}",
                color="#6366f1", size=22, shape="dot")
        
        paper_ids = {f"p_{p['id']}" for p in papers}
        
        # 作者
        if "作者关系" in relations:
            for p in papers:
                pid = f"p_{p['id']}"
                for author in p.get('authors', [])[:3]:
                    if author.strip():
                        aid = f"a_{author}"
                        if aid not in G:
                            G.add_node(aid, label=author, title=f"作者: {author}",
                                color="#f59e0b", size=15, shape="diamond")
                        G.add_edge(aid, pid, color="#e5e7eb", width=1)
        
        # 相似
        if "相似关系" in relations:
            for sim in db.get_similarities(config.similarity_threshold):
                p1, p2 = f"p_{sim['paper1_id']}", f"p_{sim['paper2_id']}"
                if p1 in paper_ids and p2 in paper_ids:
                    G.add_edge(p1, p2, color="#10b981", width=max(1, sim['score']*3),
                        title=f"相似度: {sim['score']:.0%}")
        
        # 学科
        if "学科归属" in relations:
            disc_map = {}
            for p in papers:
                d = p.get('discipline', '其他')
                if d not in disc_map:
                    disc_map[d] = []
                disc_map[d].append(f"p_{p['id']}")
            
            for d, pids in disc_map.items():
                did = f"d_{d}"
                G.add_node(did, label=f"【{d}】", title=f"{d}: {len(pids)}篇",
                    color="#ef4444", size=30, shape="star")
                for pid in pids:
                    G.add_edge(did, pid, color="#fecaca", width=1, dashes=True)
        
        return G
    
    G = build_graph()
    
    # 可视化
    net = Network(height="550px", width="100%", bgcolor="#ffffff", font_color="#333")
    net.set_options("""
    {"physics": {"barnesHut": {"gravitationalConstant": -4000, "springLength": 100},
                 "stabilization": {"iterations": 300}},
     "interaction": {"hover": true, "tooltipDelay": 50},
     "nodes": {"font": {"face": "Microsoft YaHei", "size": 11}}}
    """)
    
    for node, data in G.nodes(data=True):
        net.add_node(node, **{k: v for k, v in data.items()})
    
    for u, v, data in G.edges(data=True):
        net.add_edge(u, v, **{k: v for k, v in data.items()})
    
    # 保存
    output = config.graph_output.parent / f"graph_{discipline or 'all'}.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    net.save_graph(str(output))
    
    # 添加图例
    legend = """
    <div style="position:fixed;top:10px;left:10px;background:#fff;padding:12px 16px;border-radius:8px;
         box-shadow:0 2px 8px rgba(0,0,0,0.08);font-size:12px;z-index:1000;font-family:system-ui;">
        <div style="font-weight:600;margin-bottom:6px;">图例</div>
        <div style="margin:3px 0;"><span style="display:inline-block;width:10px;height:10px;background:#6366f1;border-radius:50%;margin-right:6px;"></span>论文</div>
        <div style="margin:3px 0;"><span style="display:inline-block;width:10px;height:10px;background:#f59e0b;transform:rotate(45deg);margin-right:6px;"></span>作者</div>
        <div style="margin:3px 0;"><span style="display:inline-block;width:10px;height:10px;background:#ef4444;clip-path:polygon(50% 0%,100% 50%,50% 100%,0% 50%);margin-right:6px;"></span>学科</div>
        <div style="margin-top:6px;padding-top:6px;border-top:1px solid #eee;color:#888;font-size:11px;">
            绿线=相似 | 虚线=归属
        </div>
    </div>
    """
    
    with open(output, 'r', encoding='utf-8') as f:
        html = f.read()
    html = html.replace('</body>', f'{legend}</body>')
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)
    
    # 显示
    with open(output, 'r', encoding='utf-8') as f:
        components.html(f.read(), height=580, scrolling=False)
    
    st.download_button("📥 下载HTML", html, "knowledge_graph.html", "text/html")
    
    # 当前学科文献
    if discipline:
        st.markdown("---")
        st.markdown(f"### 📚 {discipline}")
        for p in papers[:8]:
            st.markdown(f"• **{p.get('title', '')[:50]}...** - {', '.join(p.get('authors', [])[:2])}")
