# 📚 文献管理Agent

> 基于LLM的智能文献管理系统，支持自动分类、PDF阅读、批注和知识图谱可视化。

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ 功能特性

| 功能 | 描述 |
|------|------|
| 📄 **PDF扫描** | 自动发现指定目录下的所有PDF文献 |
| 🔍 **内容解析** | 提取标题、作者、摘要、关键词 |
| 🤖 **LLM分类** | 使用大语言模型自动判断学科领域 |
| 📁 **自动归档** | 按学科创建文件夹，按需整理文献 |
| 📖 **PDF阅读** | 内置阅读器，支持翻页、缩放、批注 |
| 🔗 **知识图谱** | 可视化展示文献关系网络 |

### 知识图谱关系
- 📊 主题相似度
- 👥 作者合作网络
- 📂 学科聚类

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动应用

```bash
streamlit run app.py
```

### 3. 初始配置

在应用的 **⚙️ 设置** 页面中配置：
- 📂 PDF输入文件夹
- 📂 输出文件夹
- 🔑 API Key

**支持的API服务：**
- DeepSeek
- OpenAI
- 智谱AI
- 其他OpenAI兼容API

## 🖼️ 界面预览

应用采用简洁白色风格设计：

- **🏠 首页** - 统计概览、快捷操作
- **📖 文献管理** - 浏览、阅读、编辑、批注
- **🔗 知识图谱** - 按学科分类的交互式图谱
- **⚙️ 设置** - 配置管理

### 阅读模式
- 全屏PDF阅读
- 首页/上页/跳页/下页/末页
- 5级缩放（1.0x ~ 2.0x）
- 批注保存

## 📁 项目结构

```
literature_agent/
├── app.py              # Streamlit主应用
├── config.py           # 默认配置
├── config_manager.py   # 动态配置管理
├── scanner.py          # PDF扫描
├── parser.py           # PDF解析
├── classifier.py       # LLM分类
├── organizer.py        # 文件归档
├── database.py         # SQLite数据库
├── knowledge_graph.py  # 知识图谱
├── main.py             # 命令行入口
├── pages/              # Streamlit页面
│   ├── literature_page.py
│   ├── graph_page.py
│   └── settings_page.py
└── requirements.txt
```

## 🔗 知识图谱

| 图形 | 含义 |
|------|------|
| 🔵 蓝色圆点 | 论文 |
| 🟡 黄色菱形 | 作者 |
| ⭐ 红色星形 | 学科分类 |

| 连线 | 含义 |
|------|------|
| 绿色实线 | 内容相似 |
| 红色虚线 | 学科归属 |
| 灰色线 | 作者-论文关系 |

## 📦 技术栈

- **Streamlit** - Web应用框架
- **PyMuPDF (fitz)** - PDF解析与渲染
- **OpenAI API** - LLM分类
- **NetworkX + Pyvis** - 知识图谱
- **SQLite** - 本地数据库
- **scikit-learn** - 文本相似度计算

## ⚠️ 注意事项

1. PDF解析质量取决于PDF本身的文本层质量
2. 扫描版PDF（图片）需要OCR支持（当前版本未集成）
3. 首次运行请先完成设置配置
4. `user_config.json` 包含API Key，已加入.gitignore

## 📄 License

MIT License
