"""
微信公众号自动化 - 选题调研 Skill
"""

import logging
from typing import List, Dict, Optional
from .base_skill import BaseSkill

# 配置日志
logger = logging.getLogger(__name__)


class TopicResearchSkill(BaseSkill):
    """选题调研"""

    def research_topic(self, topic: str, keywords: Optional[List[str]] = None) -> Dict:
        """调研选题"""
        # 参数验证
        if not topic or not isinstance(topic, str):
            logger.error("无效的topic参数: topic不能为空且必须是字符串")
            raise ValueError("topic不能为空且必须是字符串")
        
        if keywords is not None:
            if not isinstance(keywords, list):
                logger.error("无效的keywords参数: keywords必须是列表")
                raise ValueError("keywords必须是列表")
            if len(keywords) > 20:
                logger.warning(f"关键词数量过多({len(keywords)}),将限制为前20个")
                keywords = keywords[:20]

        try:
            search_query = topic
            if keywords:
                search_query = f"{topic} {' '.join(keywords)}"
            
            logger.info(f"开始调研选题: {search_query}")
            
            # 搜索 - 优先使用 Tavily，其次用简单 HTTP 搜索
            results = self._search_web(search_query)
            
            if not results:
                # 降级：使用模拟数据
                results = [{"title": f"关于 {topic} 的研究", "url": "https://example.com", "snippet": "暂无搜索结果"}]
            
            logger.info(f"选题调研完成: {topic}, 找到 {len(results)} 条结果")
            
            # 提取相关主题
            related = self._extract_related_topics(results)
            
            return {
                "topic": topic,
                "keywords": keywords or [],
                "search_results": results[:10],
                "summary": self._generate_summary(topic, results),
                "related_topics": related
            }
        except Exception as e:
            logger.error(f"选题调研失败: {str(e)}", exc_info=True)
            raise
    
    def _search_web(self, query: str, limit: int = 10) -> List[Dict]:
        """网络搜索"""
        import os
        import requests
        
        # 优先使用 Tavily
        tavily_key = os.environ.get("TAVILY_API_KEY", "")
        if tavily_key:
            try:
                resp = requests.post(
                    "https://api.tavily.com/search",
                    json={"query": query, "max_results": limit},
                    headers={"Content-Type": "application/json"},
                    timeout=15
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for item in data.get("results", []):
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("content", "")
                        })
                    logger.info(f"Tavily 搜索成功: {len(results)} 条结果")
                    return results
            except Exception as e:
                logger.warning(f"Tavily 搜索失败: {str(e)}")
        
        # 备选：使用 DuckDuckGo (无需 API key)
        try:
            ddg_url = "https://duckduckgo.com/"
            params = {"q": query, "format": "json", "no_html": "1"}
            resp = requests.get(ddg_url, params=params, timeout=15)
            
            # DuckDuckGo API 需要特殊处理
            # 使用 HTML 搜索作为降级
            from urllib.parse import quote
            html_url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
            resp = requests.get(html_url, timeout=15)
            
            if resp.status_code == 200:
                import re
                # 简单解析 HTML 结果
                items = re.findall(r'<a class="result__a" href="([^"]+)"[^>]*>(.+?)</a>', resp.text)
                results = []
                for url, title in items[:limit]:
                    # 提取实际 URL（DuckDuckGo 重定向）
                    results.append({
                        "title": re.sub(r'<[^>]+>', '', title),
                        "url": url,
                        "snippet": ""
                    })
                if results:
                    logger.info(f"DuckDuckGo 搜索成功: {len(results)} 条结果")
                    return results
        except Exception as e:
            logger.warning(f"搜索失败: {str(e)}")
        
        return []
    
    def _extract_related_topics(self, search_results: List[Dict]) -> List[str]:
        """从搜索结果中提取相关主题"""
        # 简单实现：提取标题中的关键词
        import re
        all_words = []
        
        for result in search_results:
            title = result.get("title", "")
            # 提取中文和英文词
            chinese = re.findall(r'[\u4e00-\u9fff]{2,}', title)
            english = re.findall(r'[a-zA-Z]{3,}', title)
            all_words.extend(chinese)
            all_words.extend(english)
        
        # 统计词频
        from collections import Counter
        word_count = Counter(all_words)
        
        # 返回最常见的主题词
        return [word for word, _ in word_count.most_common(5)]
    
    def _generate_summary(self, topic: str, search_results: List[Dict]) -> str:
        """生成摘要"""
        if not search_results:
            return f"暂无关于 {topic} 的搜索结果"
        
        snippet = search_results[0].get("snippet", "")[:200]
        if snippet:
            return f"最新动态：{snippet}..."
        
        return f"关于 {topic}，已找到 {len(search_results)} 条相关资料"

    def generate_outline(self, topic: str, research_data: Dict) -> Dict:
        """生成大纲"""
        # 参数验证
        if not topic or not isinstance(topic, str):
            logger.error("无效的topic参数: topic不能为空且必须是字符串")
            raise ValueError("topic不能为空且必须是字符串")
        
        if research_data is not None and not isinstance(research_data, dict):
            logger.error("无效的research_data参数: research_data必须是字典")
            raise ValueError("research_data必须是字典")

        try:
            logger.info(f"为选题生成大纲: {topic}")
            
            result = {
                "title": f"深度解析：{topic}",
                "sections": [
                    {"name": "引言", "description": "背景介绍", "key_points": ["背景", "重要性"]},
                    {"name": "核心内容", "description": "关键要素", "key_points": ["要点1", "要点2"]},
                    {"name": "结论", "description": "总结", "key_points": ["结论", "建议"]}
                ],
                "estimated_words": 2000
            }
            
            logger.info(f"大纲生成完成: {topic}")
            return result
        except Exception as e:
            logger.error(f"大纲生成失败: {str(e)}", exc_info=True)
            raise
