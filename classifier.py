"""
LLM分类模块
使用大语言模型对文献进行学科分类
"""
import json
from typing import Dict, List, Optional
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME, DISCIPLINES


class LiteratureClassifier:
    """基于LLM的文献分类器"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        # 支持动态配置
        from config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME
        self.client = OpenAI(
            api_key=api_key or OPENAI_API_KEY,
            base_url=base_url or OPENAI_BASE_URL
        )
        self.model = model or MODEL_NAME
    
    def classify(self, title: str, abstract: str, keywords: List[str] = None) -> Dict:
        """
        对文献进行学科分类
        
        Args:
            title: 文献标题
            abstract: 摘要
            keywords: 关键词列表
        
        Returns:
            分类结果字典
        """
        prompt = self._build_prompt(title, abstract, keywords)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个学术文献分类专家，擅长判断论文的学科领域和类型。请始终返回有效的JSON格式。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500,
            )
            
            result_text = response.choices[0].message.content
            # 提取JSON
            result = self._parse_json_response(result_text)
            return result
            
        except Exception as e:
            print(f"[错误] LLM分类失败: {e}")
            return {
                "discipline": "其他",
                "sub_field": "未知",
                "paper_type": "未知",
                "confidence": 0.0,
                "summary": "",
                "error": str(e)
            }
    
    def _build_prompt(self, title: str, abstract: str, keywords: List[str] = None) -> str:
        """构建分类提示词"""
        disciplines_str = "、".join(DISCIPLINES)
        keywords_str = "、".join(keywords) if keywords else "无"
        
        prompt = f"""请分析以下学术文献，判断其学科分类：

## 文献信息
- **标题**: {title}
- **摘要**: {abstract if abstract else "无摘要"}
- **关键词**: {keywords_str}

## 分类要求
1. 从以下学科中选择**最匹配**的一个：{disciplines_str}
2. 判断文献的细分领域
3. 判断文献类型（综述Review、实验研究Experimental、理论分析Theoretical、案例研究Case Study、方法论Methodology）
4. 给出分类置信度（0-1）
5. 用一句话概括文献核心内容

## 返回格式（JSON）
```json
{{
    "discipline": "主学科名称",
    "sub_field": "细分领域",
    "paper_type": "文献类型",
    "confidence": 0.95,
    "summary": "一句话概括"
}}
```

请直接返回JSON，不要添加其他内容。"""
        
        return prompt
    
    def _parse_json_response(self, text: str) -> Dict:
        """解析LLM返回的JSON"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except:
            pass
        
        # 尝试提取代码块中的JSON
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        
        # 尝试找到JSON对象
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # 返回默认值
        return {
            "discipline": "其他",
            "sub_field": "未知",
            "paper_type": "未知",
            "confidence": 0.0,
            "summary": ""
        }
    
    def batch_classify(self, papers: List[Dict]) -> List[Dict]:
        """
        批量分类文献
        
        Args:
            papers: 文献列表，每个包含title, abstract, keywords
        
        Returns:
            分类结果列表
        """
        results = []
        total = len(papers)
        
        for i, paper in enumerate(papers):
            print(f"[分类] 正在处理 ({i+1}/{total}): {paper.get('title', '未知')[:50]}...")
            
            result = self.classify(
                title=paper.get("title", ""),
                abstract=paper.get("abstract", ""),
                keywords=paper.get("keywords", [])
            )
            result["file_path"] = paper.get("file_path", "")
            results.append(result)
        
        return results


def classify_paper(title: str, abstract: str, keywords: List[str] = None) -> Dict:
    """
    便捷函数：分类单篇文献
    """
    classifier = LiteratureClassifier()
    return classifier.classify(title, abstract, keywords)


if __name__ == "__main__":
    # 测试分类
    test_title = "Deep Learning for Natural Language Processing: A Survey"
    test_abstract = """
    This paper provides a comprehensive survey of deep learning techniques 
    applied to natural language processing (NLP). We review the development 
    of neural network architectures from RNNs to Transformers, and discuss 
    their applications in machine translation, sentiment analysis, and 
    question answering systems.
    """
    test_keywords = ["deep learning", "NLP", "transformer", "neural network"]
    
    result = classify_paper(test_title, test_abstract, test_keywords)
    print(json.dumps(result, ensure_ascii=False, indent=2))
