"""
设置页面 - 配置输入/输出文件夹和API
"""
import streamlit as st
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_manager import load_config, save_config, AppConfig

st.markdown('<p class="main-title">⚙️ 设置</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">配置应用参数</p>', unsafe_allow_html=True)

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
        placeholder="https://api.openai.com/v1",
        help="API服务地址"
    )

with col2:
    model_name = st.selectbox(
        "模型",
        options=["deepseek-chat", "gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "glm-4"],
        index=["deepseek-chat", "gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "glm-4"].index(config.model_name) if config.model_name in ["deepseek-chat", "gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "glm-4"] else 0
    )

# 常用API预设
st.markdown("**快捷预设：**")
preset_col1, preset_col2, preset_col3 = st.columns(3)

with preset_col1:
    if st.button("DeepSeek", use_container_width=True):
        api_base_url = "https://api.deepseek.com"
        model_name = "deepseek-chat"
        st.rerun()

with preset_col2:
    if st.button("OpenAI", use_container_width=True):
        api_base_url = "https://api.openai.com/v1"
        model_name = "gpt-4o-mini"
        st.rerun()

with preset_col3:
    if st.button("智谱AI", use_container_width=True):
        api_base_url = "https://open.bigmodel.cn/api/paas/v4"
        model_name = "glm-4"
        st.rerun()

st.markdown("---")

# 高级设置
with st.expander("🔧 高级设置"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        max_pages = st.number_input(
            "解析页数",
            min_value=1,
            max_value=20,
            value=config.max_pages_to_parse,
            help="解析PDF的前N页提取信息"
        )
    
    with col2:
        max_abstract = st.number_input(
            "摘要最大长度",
            min_value=500,
            max_value=5000,
            value=config.max_abstract_length,
            step=500
        )
    
    with col3:
        similarity_threshold = st.slider(
            "相似度阈值",
            min_value=0.3,
            max_value=0.9,
            value=config.similarity_threshold,
            step=0.1,
            help="高于此阈值的文献会建立相似关系"
        )

st.markdown("---")

# 保存按钮
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    if st.button("💾 保存配置", type="primary", use_container_width=True):
        # 更新配置
        config.input_folder = input_folder
        config.output_folder = output_folder
        config.api_key = api_key
        config.api_base_url = api_base_url
        config.model_name = model_name
        config.max_pages_to_parse = max_pages
        config.max_abstract_length = max_abstract
        config.similarity_threshold = similarity_threshold
        
        # 创建输出目录
        if output_folder:
            Path(output_folder).mkdir(parents=True, exist_ok=True)
        
        # 保存
        save_config(config)
        st.session_state.config = config
        st.success("✓ 配置已保存！")
        st.balloons()

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
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=5
                )
                st.success("✓ API连接成功！")
            except Exception as e:
                st.error(f"✗ API连接失败: {e}")
        else:
            st.warning("请先输入API Key")

# 当前配置状态
st.markdown("---")
st.markdown("### 📋 当前配置状态")

valid, msg = config.validate()
if valid:
    st.success(f"✓ {msg}")
    st.json({
        "输入文件夹": config.input_folder,
        "输出文件夹": config.output_folder,
        "API服务": config.api_base_url,
        "模型": config.model_name
    })
else:
    st.warning(f"⚠️ {msg}")
