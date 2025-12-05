"""
设置页面 - 配置输入/输出文件夹和API
"""
import streamlit as st
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_manager import load_config, save_config, AppConfig


def render():
    st.markdown("## ⚙️ 设置")
    st.caption("配置应用参数")
    
    # 加载配置
    if 'config' not in st.session_state:
        st.session_state.config = load_config()
    
    config = st.session_state.config
    
    # 文件夹配置
    st.markdown("### 📁 文件夹配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        input_folder = st.text_input(
            "输入文件夹（PDF源目录）",
            value=config.input_folder,
            placeholder="例如: D:/文献/PDF",
            help="存放原始PDF文献的文件夹"
        )
    
    with col2:
        output_folder = st.text_input(
            "输出文件夹",
            value=config.output_folder,
            placeholder="例如: D:/文献/输出",
            help="分类文献、数据库、知识图谱的存放位置"
        )
    
    # 验证文件夹
    if input_folder:
        if Path(input_folder).exists():
            pdf_count = len(list(Path(input_folder).rglob("*.pdf")))
            st.success(f"✓ 输入文件夹有效，发现 {pdf_count} 个PDF文件")
        else:
            st.error("✗ 输入文件夹不存在")
    
    st.markdown("---")
    
    # API配置
    st.markdown("### 🔑 API配置")
    
    api_key = st.text_input(
        "API Key",
        value=config.api_key,
        type="password",
        placeholder="sk-xxxxx",
        help="OpenAI兼容API的密钥"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        api_base_url = st.text_input(
            "API Base URL",
            value=config.api_base_url,
            placeholder="https://api.openai.com/v1"
        )
    
    with col2:
        model_options = ["deepseek-chat", "gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "glm-4"]
        current_index = model_options.index(config.model_name) if config.model_name in model_options else 0
        model_name = st.selectbox("模型", options=model_options, index=current_index)
    
    # 快捷预设
    st.markdown("**快捷预设：**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("DeepSeek", use_container_width=True):
            config.api_base_url = "https://api.deepseek.com"
            config.model_name = "deepseek-chat"
            st.session_state.config = config
            st.rerun()
    
    with col2:
        if st.button("OpenAI", use_container_width=True):
            config.api_base_url = "https://api.openai.com/v1"
            config.model_name = "gpt-4o-mini"
            st.session_state.config = config
            st.rerun()
    
    with col3:
        if st.button("智谱AI", use_container_width=True):
            config.api_base_url = "https://open.bigmodel.cn/api/paas/v4"
            config.model_name = "glm-4"
            st.session_state.config = config
            st.rerun()
    
    st.markdown("---")
    
    # 高级设置
    with st.expander("🔧 高级设置"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            max_pages = st.number_input(
                "解析页数", min_value=1, max_value=20,
                value=config.max_pages_to_parse
            )
        
        with col2:
            max_abstract = st.number_input(
                "摘要最大长度", min_value=500, max_value=5000,
                value=config.max_abstract_length, step=500
            )
        
        with col3:
            similarity_threshold = st.slider(
                "相似度阈值", min_value=0.3, max_value=0.9,
                value=config.similarity_threshold, step=0.1
            )
    
    st.markdown("---")
    
    # 保存按钮
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button("💾 保存配置", type="primary", use_container_width=True):
            config.input_folder = input_folder
            config.output_folder = output_folder
            config.api_key = api_key
            config.api_base_url = api_base_url
            config.model_name = model_name
            config.max_pages_to_parse = max_pages
            config.max_abstract_length = max_abstract
            config.similarity_threshold = similarity_threshold
            
            if output_folder:
                Path(output_folder).mkdir(parents=True, exist_ok=True)
            
            save_config(config)
            st.session_state.config = config
            st.success("✓ 配置已保存！")
    
    with col2:
        if st.button("🔄 重置", use_container_width=True):
            st.session_state.config = AppConfig()
            st.rerun()
    
    with col3:
        if st.button("🧪 测试API", use_container_width=True):
            if api_key:
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=api_key, base_url=api_base_url)
                    client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "user", "content": "Hi"}],
                        max_tokens=5
                    )
                    st.success("✓ API连接成功！")
                except Exception as e:
                    st.error(f"✗ 连接失败: {e}")
            else:
                st.warning("请先输入API Key")
    
    # 状态
    st.markdown("---")
    valid, msg = config.validate()
    if valid:
        st.success(f"✓ {msg}")
    else:
        st.warning(f"⚠️ {msg}")
