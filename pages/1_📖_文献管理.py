"""
文献管理页面 - 浏览、阅读、编辑文献
"""
import streamlit as st
from pathlib import Path
import sys
import fitz  # PyMuPDF
import base64

sys.path.insert(0, str(Path(__file__).parent.parent))

from config_manager import load_config

st.markdown('<p class="main-title">📖 文献管理</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">浏览、阅读和编辑您的文献</p>', unsafe_allow_html=True)

# 加载配置
if 'config' not in st.session_state:
    st.session_state.config = load_config()

config = st.session_state.config

if not config.is_configured():
    st.warning("⚠️ 请先完成设置后再使用此功能")
    st.stop()

# 导入核心模块
from database import LiteratureDatabase
from scanner import scan_pdfs
from parser import parse_pdf
from classifier import LiteratureClassifier
from organizer import FileOrganizer

# 初始化数据库
db = LiteratureDatabase(config.database_path)

# 顶部操作栏
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    search_query = st.text_input("🔍 搜索文献", placeholder="输入标题、作者或关键词...")

with col2:
    discipline_filter = st.selectbox(
        "📂 学科筛选",
        ["全部"] + config.disciplines
    )

with col3:
    if st.button("🔄 扫描新文献", type="primary", use_container_width=True):
        st.session_state.show_scan = True

# 扫描新文献
if st.session_state.get('show_scan', False):
    st.markdown("---")
    st.markdown("### 🔄 扫描并处理新文献")
    
    with st.spinner("正在扫描PDF文件..."):
        pdfs = scan_pdfs(config.pdf_source_dir)
    
    if pdfs:
        st.info(f"发现 {len(pdfs)} 个PDF文件")
        
        # 获取已处理的文件
        existing_papers = db.get_all_papers()
        existing_paths = {p['file_path'] for p in existing_papers}
        
        new_pdfs = [p for p in pdfs if str(p) not in existing_paths]
        
        if new_pdfs:
            st.success(f"其中 {len(new_pdfs)} 个为新文献")
            
            if st.button("开始处理新文献"):
                classifier = LiteratureClassifier(
                    api_key=config.api_key,
                    base_url=config.api_base_url,
                    model=config.model_name
                )
                organizer = FileOrganizer(config.classified_dir)
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, pdf_path in enumerate(new_pdfs):
                    status_text.text(f"处理中: {pdf_path.name}")
                    
                    # 解析
                    metadata = parse_pdf(pdf_path)
                    
                    # 分类
                    classification = classifier.classify(
                        title=metadata.get("title", ""),
                        abstract=metadata.get("abstract", ""),
                        keywords=metadata.get("keywords", [])
                    )
                    
                    # 保存到数据库
                    db.add_paper(metadata, classification)
                    
                    # 归档
                    organizer.organize(
                        pdf_path,
                        classification.get("discipline", "其他"),
                        classification.get("sub_field"),
                        copy=True
                    )
                    
                    progress_bar.progress((i + 1) / len(new_pdfs))
                
                status_text.text("✓ 处理完成！")
                st.success(f"成功处理 {len(new_pdfs)} 篇文献")
                st.session_state.show_scan = False
                st.rerun()
        else:
            st.info("没有发现新文献")
    else:
        st.warning("未找到PDF文件")
    
    if st.button("关闭"):
        st.session_state.show_scan = False
        st.rerun()

st.markdown("---")

# 获取文献列表
papers = db.get_all_papers()

# 筛选
if search_query:
    papers = [p for p in papers if 
              search_query.lower() in p.get('title', '').lower() or
              search_query.lower() in str(p.get('authors', [])).lower() or
              search_query.lower() in str(p.get('keywords', [])).lower()]

if discipline_filter != "全部":
    papers = [p for p in papers if p.get('discipline') == discipline_filter]

# 显示文献列表
st.markdown(f"### 📚 文献列表 ({len(papers)})")

if not papers:
    st.info("暂无文献，请先扫描处理")
else:
    # 分页
    items_per_page = 10
    total_pages = max(1, (len(papers) + items_per_page - 1) // items_per_page)
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    
    # 文献卡片
    start_idx = (st.session_state.current_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    for paper in papers[start_idx:end_idx]:
        with st.container():
            col1, col2, col3 = st.columns([5, 2, 1])
            
            with col1:
                st.markdown(f"**{paper.get('title', '未知标题')[:80]}**")
                authors = ', '.join(paper.get('authors', [])[:3])
                if len(paper.get('authors', [])) > 3:
                    authors += ' 等'
                st.caption(f"👤 {authors or '未知'} · 📂 {paper.get('discipline', '未分类')} · 📄 {paper.get('page_count', 0)}页")
            
            with col2:
                st.caption(f"类型: {paper.get('paper_type', '未知')}")
                st.caption(f"置信度: {paper.get('confidence', 0):.0%}")
            
            with col3:
                if st.button("查看", key=f"view_{paper['id']}", use_container_width=True):
                    st.session_state.selected_paper = paper
                    st.session_state.show_detail = True
        
        st.markdown("---")
    
    # 分页控制
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        page = st.selectbox(
            "页码",
            range(1, total_pages + 1),
            index=st.session_state.current_page - 1,
            label_visibility="collapsed"
        )
        if page != st.session_state.current_page:
            st.session_state.current_page = page
            st.rerun()

# 文献详情弹窗
if st.session_state.get('show_detail', False) and st.session_state.get('selected_paper'):
    paper = st.session_state.selected_paper
    
    st.markdown("---")
    st.markdown("## 📄 文献详情")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # PDF预览
        pdf_path = paper.get('file_path')
        if pdf_path and Path(pdf_path).exists():
            try:
                doc = fitz.open(pdf_path)
                # 显示第一页
                page = doc[0]
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                img_bytes = pix.tobytes("png")
                st.image(img_bytes, caption="第1页预览", use_container_width=True)
                doc.close()
            except Exception as e:
                st.warning(f"PDF预览失败: {e}")
        else:
            st.info("PDF文件不存在")
    
    with col2:
        # 元数据编辑
        st.markdown("### 编辑信息")
        
        new_title = st.text_input("标题", value=paper.get('title', ''))
        new_discipline = st.selectbox(
            "学科",
            config.disciplines,
            index=config.disciplines.index(paper.get('discipline', '其他')) if paper.get('discipline') in config.disciplines else -1
        )
        new_type = st.selectbox(
            "类型",
            ["综述", "实验研究", "理论分析", "案例研究", "方法论", "其他"],
            index=["综述", "实验研究", "理论分析", "案例研究", "方法论", "其他"].index(paper.get('paper_type', '其他')) if paper.get('paper_type') in ["综述", "实验研究", "理论分析", "案例研究", "方法论", "其他"] else 5
        )
        
        st.markdown("**摘要:**")
        st.text_area("", value=paper.get('abstract', '')[:500], height=150, disabled=True, label_visibility="collapsed")
        
        st.markdown("**关键词:**")
        st.caption(', '.join(paper.get('keywords', [])))
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("💾 保存修改", type="primary", use_container_width=True):
                # 更新数据库
                paper['title'] = new_title
                paper['discipline'] = new_discipline
                paper['paper_type'] = new_type
                db.add_paper(paper, {'discipline': new_discipline, 'paper_type': new_type})
                st.success("已保存")
        
        with col_b:
            if st.button("❌ 关闭", use_container_width=True):
                st.session_state.show_detail = False
                st.rerun()
