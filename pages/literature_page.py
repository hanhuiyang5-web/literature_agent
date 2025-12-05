"""
文献管理页面 - 浏览、阅读、编辑文献
"""
import streamlit as st
from pathlib import Path
import sys
import fitz

sys.path.insert(0, str(Path(__file__).parent.parent))


def render(config):
    if not config.is_configured():
        st.warning("⚠️ 请先完成设置后再使用此功能")
        return
    
    from database import LiteratureDatabase
    from scanner import scan_pdfs
    from parser import parse_pdf
    from classifier import LiteratureClassifier
    from organizer import FileOrganizer
    
    db = LiteratureDatabase(config.database_path)
    
    # 初始化状态
    if 'selected_id' not in st.session_state:
        st.session_state.selected_id = None
    if 'pdf_page' not in st.session_state:
        st.session_state.pdf_page = 0
    if 'zoom_level' not in st.session_state:
        st.session_state.zoom_level = 1.5
    if 'notes' not in st.session_state:
        st.session_state.notes = {}
    
    # ==================== 阅读模式 ====================
    if st.session_state.selected_id:
        paper = db.get_paper_by_id(st.session_state.selected_id)
        if not paper:
            st.session_state.selected_id = None
            st.rerun()
            return
        
        pdf_path = paper.get('file_path')
        
        # 顶部工具栏
        tool_col1, tool_col2, tool_col3, tool_col4 = st.columns([1, 4, 2, 1])
        
        with tool_col1:
            if st.button("← 返回", use_container_width=True):
                st.session_state.selected_id = None
                st.session_state.pdf_page = 0
                st.rerun()
        
        with tool_col2:
            st.markdown(f"**📄 {paper.get('title', '未知')[:50]}...**")
        
        with tool_col3:
            st.caption(f"📂 {paper.get('discipline', '-')} | {paper.get('paper_type', '-')}")
        
        with tool_col4:
            zoom = st.selectbox("缩放", [1.0, 1.25, 1.5, 1.75, 2.0], 
                               index=[1.0, 1.25, 1.5, 1.75, 2.0].index(st.session_state.zoom_level),
                               label_visibility="collapsed")
            if zoom != st.session_state.zoom_level:
                st.session_state.zoom_level = zoom
                st.rerun()
        
        st.markdown("---")
        
        # 主阅读区域：左PDF 右工具
        pdf_col, tool_col = st.columns([7, 3])
        
        with pdf_col:
            if pdf_path and Path(pdf_path).exists():
                try:
                    doc = fitz.open(pdf_path)
                    total_pages = len(doc)
                    
                    # 翻页控制栏
                    nav1, nav2, nav3, nav4, nav5 = st.columns([1, 1, 2, 1, 1])
                    
                    with nav1:
                        if st.button("⏮ 首页", use_container_width=True, disabled=st.session_state.pdf_page <= 0):
                            st.session_state.pdf_page = 0
                            st.rerun()
                    
                    with nav2:
                        if st.button("◀ 上页", use_container_width=True, disabled=st.session_state.pdf_page <= 0):
                            st.session_state.pdf_page -= 1
                            st.rerun()
                    
                    with nav3:
                        jump_page = st.number_input(
                            "跳转", min_value=1, max_value=total_pages,
                            value=st.session_state.pdf_page + 1,
                            label_visibility="collapsed"
                        )
                        if jump_page - 1 != st.session_state.pdf_page:
                            st.session_state.pdf_page = jump_page - 1
                            st.rerun()
                        st.caption(f"共 {total_pages} 页")
                    
                    with nav4:
                        if st.button("下页 ▶", use_container_width=True, disabled=st.session_state.pdf_page >= total_pages - 1):
                            st.session_state.pdf_page += 1
                            st.rerun()
                    
                    with nav5:
                        if st.button("末页 ⏭", use_container_width=True, disabled=st.session_state.pdf_page >= total_pages - 1):
                            st.session_state.pdf_page = total_pages - 1
                            st.rerun()
                    
                    # 渲染PDF页面
                    page_num = min(st.session_state.pdf_page, total_pages - 1)
                    page = doc[page_num]
                    pix = page.get_pixmap(matrix=fitz.Matrix(st.session_state.zoom_level, st.session_state.zoom_level))
                    st.image(pix.tobytes("png"), use_column_width=True)
                    doc.close()
                    
                except Exception as e:
                    st.error(f"PDF加载失败: {e}")
            else:
                st.warning(f"PDF文件不存在: {pdf_path}")
        
        with tool_col:
            tab1, tab2 = st.tabs(["📋 信息", "📝 批注"])
            
            with tab1:
                st.markdown("**标题**")
                new_title = st.text_input("标题", value=paper.get('title', ''), label_visibility="collapsed")
                
                st.markdown("**作者**")
                st.caption(', '.join(paper.get('authors', [])) or '未知')
                
                st.markdown("**学科**")
                disc_idx = config.disciplines.index(paper.get('discipline')) if paper.get('discipline') in config.disciplines else len(config.disciplines) - 1
                new_disc = st.selectbox("学科", config.disciplines, index=disc_idx, label_visibility="collapsed")
                
                st.markdown("**类型**")
                types = ["综述", "实验研究", "理论分析", "案例研究", "方法论", "其他"]
                type_idx = types.index(paper.get('paper_type')) if paper.get('paper_type') in types else len(types) - 1
                new_type = st.selectbox("类型", types, index=type_idx, label_visibility="collapsed")
                
                st.markdown("**关键词**")
                st.caption(', '.join(paper.get('keywords', [])) or '无')
                
                if st.button("💾 保存信息", type="primary", use_container_width=True):
                    paper['title'] = new_title
                    paper['discipline'] = new_disc
                    paper['paper_type'] = new_type
                    db.add_paper(paper, {'discipline': new_disc, 'paper_type': new_type})
                    st.success("✓ 已保存")
            
            with tab2:
                st.markdown("**我的批注**")
                paper_id = paper['id']
                current_notes = st.session_state.notes.get(paper_id, paper.get('notes', '') or '')
                
                notes_text = st.text_area(
                    "批注内容",
                    value=current_notes,
                    height=300,
                    placeholder="在这里记录你的想法、笔记...",
                    label_visibility="collapsed"
                )
                
                if st.button("💾 保存批注", use_container_width=True):
                    st.session_state.notes[paper_id] = notes_text
                    db.update_notes(paper_id, notes_text)
                    st.success("✓ 批注已保存")
                
                st.markdown("---")
                st.markdown("**摘要**")
                abstract = paper.get('abstract', '无') or '无'
                st.caption(abstract[:300] + '...' if len(abstract) > 300 else abstract)
        
        return  # 阅读模式独占页面
    
    # ========== 列表页面 ==========
    # 顶部操作栏
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search_query = st.text_input("🔍 搜索", placeholder="标题、作者或关键词...", label_visibility="collapsed")
    
    with col2:
        discipline_filter = st.selectbox("📂 筛选", ["全部"] + config.disciplines, label_visibility="collapsed")
    
    with col3:
        scan_btn = st.button("🔄 扫描新文献", type="primary", use_container_width=True)
    
    # 扫描逻辑
    if scan_btn:
        with st.spinner("扫描中..."):
            pdfs = scan_pdfs(config.pdf_source_dir)
        
        if pdfs:
            existing = {p['file_path'] for p in db.get_all_papers()}
            new_pdfs = [p for p in pdfs if str(p) not in existing]
            
            if new_pdfs:
                st.info(f"发现 {len(new_pdfs)} 个新文献，开始处理...")
                
                classifier = LiteratureClassifier(
                    api_key=config.api_key,
                    base_url=config.api_base_url,
                    model=config.model_name
                )
                organizer = FileOrganizer(config.classified_dir)
                
                progress = st.progress(0)
                status = st.empty()
                
                for i, pdf in enumerate(new_pdfs):
                    status.text(f"处理: {pdf.name}")
                    metadata = parse_pdf(pdf)
                    classification = classifier.classify(
                        metadata.get("title", ""),
                        metadata.get("abstract", ""),
                        metadata.get("keywords", [])
                    )
                    db.add_paper(metadata, classification)
                    organizer.organize(pdf, classification.get("discipline", "其他"), classification.get("sub_field"), True)
                    progress.progress((i + 1) / len(new_pdfs))
                
                status.text("✓ 完成！")
                st.success(f"处理完成 {len(new_pdfs)} 篇")
                st.rerun()
            else:
                st.info("没有新文献")
        else:
            st.warning("未找到PDF")
    
    st.markdown("---")
    
    # 文献列表
    papers = db.get_all_papers()
    
    if search_query:
        q = search_query.lower()
        papers = [p for p in papers if q in p.get('title', '').lower() or q in str(p.get('authors', [])).lower()]
    
    if discipline_filter != "全部":
        papers = [p for p in papers if p.get('discipline') == discipline_filter]
    
    st.markdown(f"### 📚 文献列表 ({len(papers)})")
    
    if not papers:
        st.info("暂无文献，请先扫描处理")
        return
    
    # 列表
    for paper in papers[:20]:
        with st.container():
            col1, col2 = st.columns([5, 1])
            
            with col1:
                st.markdown(f"**{paper.get('title', '未知')[:70]}**")
                authors = ', '.join(paper.get('authors', [])[:2])
                st.caption(f"👤 {authors or '未知'} · 📂 {paper.get('discipline', '-')} · {paper.get('paper_type', '-')}")
            
            with col2:
                if st.button("查看", key=f"v_{paper['id']}", use_container_width=True):
                    st.session_state.selected_id = paper['id']
                    st.session_state.pdf_page = 0
                    st.rerun()
        
        st.divider()
