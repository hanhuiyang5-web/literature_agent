"""
文献管理Agent - Streamlit应用主入口
v1.1 - 桌面应用版本
"""
import streamlit as st
from pathlib import Path

# 页面配置 - 必须在最前面
st.set_page_config(
    page_title="文献管理Agent",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义白色简洁样式
st.markdown("""
<style>
    /* 主背景白色 */
    .stApp {
        background-color: #ffffff;
    }
    
    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background-color: #fafafa;
        border-right: 1px solid #eee;
    }
    
    /* 隐藏Streamlit默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 卡片样式 */
    .card {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    
    /* 标题样式 */
    .main-title {
        font-size: 28px;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 8px;
    }
    
    .sub-title {
        font-size: 14px;
        color: #666;
        margin-bottom: 24px;
    }
    
    /* 统计卡片 */
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 20px;
        color: white;
        text-align: center;
    }
    
    .stat-number {
        font-size: 36px;
        font-weight: 700;
    }
    
    .stat-label {
        font-size: 14px;
        opacity: 0.9;
    }
    
    /* 按钮样式 */
    .stButton > button {
        background-color: #4F46E5;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 24px;
        font-weight: 500;
    }
    
    .stButton > button:hover {
        background-color: #4338CA;
    }
    
    /* 输入框样式 */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 1px solid #e0e0e0;
    }
    
    /* 选择框样式 */
    .stSelectbox > div > div {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

from config_manager import load_config, save_config, AppConfig

# 初始化session state
if 'config' not in st.session_state:
    st.session_state.config = load_config()

config = st.session_state.config

# 侧边栏导航
with st.sidebar:
    st.markdown("## 📚 文献管理")
    st.markdown("---")
    
    # 导航菜单
    page = st.radio(
        "导航",
        ["🏠 首页", "📖 文献管理", "🔗 知识图谱", "⚙️ 设置"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # 统计面板
    if config.is_configured():
        try:
            from database import LiteratureDatabase
            db = LiteratureDatabase(config.database_path)
            stats = db.get_statistics()
            
            st.markdown("### 📊 统计")
            st.markdown(f"**{stats.get('total_papers', 0)}** 篇文献")
            
            # 按学科显示
            by_disc = stats.get('by_discipline', {})
            if by_disc:
                st.markdown("---")
                st.markdown("**按学科分布**")
                for disc, count in sorted(by_disc.items(), key=lambda x: -x[1])[:5]:
                    st.caption(f"• {disc}: {count}篇")
                if len(by_disc) > 5:
                    st.caption(f"  ...还有{len(by_disc)-5}个学科")
        except:
            pass
        
        st.markdown("---")
        st.success("✓ 已配置")
    else:
        st.warning("⚠️ 未配置")
        st.caption("请先完成设置")
    
    # 底部信息
    st.markdown("---")
    st.caption("v1.1 | 智能文献分类")

# 页面路由
if page == "🏠 首页":
    st.markdown('<p class="main-title">📚 文献管理Agent</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">智能文献分类与知识图谱构建系统</p>', unsafe_allow_html=True)
    
    if not config.is_configured():
        st.info("👋 欢迎使用！请先前往 **设置** 页面完成初始配置。")
    else:
        # 统计信息
        col1, col2, col3, col4 = st.columns(4)
        
        # 尝试获取统计数据
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from database import LiteratureDatabase
            db = LiteratureDatabase(config.database_path)
            stats = db.get_statistics()
            
            with col1:
                st.metric("📄 文献总数", stats.get('total_papers', 0))
            with col2:
                st.metric("👤 作者数", stats.get('total_authors', 0))
            with col3:
                st.metric("📂 学科数", len(stats.get('by_discipline', {})))
            with col4:
                # 计算今日新增（简化处理）
                st.metric("🆕 今日处理", "-")
        except:
            with col1:
                st.metric("📄 文献总数", 0)
            with col2:
                st.metric("👤 作者数", 0)
            with col3:
                st.metric("📂 学科数", 0)
            with col4:
                st.metric("🆕 今日处理", 0)
        
        st.markdown("---")
        
        # 快捷操作
        st.markdown("### 快捷操作")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 扫描并处理新文献", use_container_width=True):
                st.switch_page("pages/1_📖_文献管理.py")
        
        with col2:
            if st.button("🔗 查看知识图谱", use_container_width=True):
                st.switch_page("pages/2_🔗_知识图谱.py")
        
        with col3:
            if st.button("⚙️ 修改设置", use_container_width=True):
                st.switch_page("pages/3_⚙️_设置.py")
        
        st.markdown("---")
        
        # 最近文献
        st.markdown("### 最近添加")
        try:
            papers = db.get_all_papers()[:5]
            if papers:
                for paper in papers:
                    with st.container():
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"**{paper.get('title', '未知标题')[:60]}...**")
                            st.caption(f"📂 {paper.get('discipline', '未分类')} · 👤 {', '.join(paper.get('authors', [])[:2]) or '未知'}")
                        with col2:
                            st.caption(f"ID: {paper.get('id')}")
            else:
                st.info("暂无文献，请先扫描处理")
        except:
            st.info("暂无数据")

elif page == "📖 文献管理":
    from pages import literature_page
    literature_page.render(config)

elif page == "🔗 知识图谱":
    from pages import graph_page
    graph_page.render(config)

elif page == "⚙️ 设置":
    from pages import settings_page
    settings_page.render()
