"""
微信公众号自动化 - 选题调研 Skill
支持级联搜索：Tavily → DuckDuckGo → 百度
"""

import os
import re
import time
import logging
from typing import List, Dict, Optional
from collections import Counter
from .base_skill import BaseSkill

# 配置日志
logger = logging.getLogger(__name__)

# 搜索Provider注册表（按优先级排序）
SEARCH_PROVIDER_REGISTRY = [
    {
        "name": "tavily",
        "priority": 1,
        "requires_key": True,
        "env_var": "TAVILY_API_KEY",
        "method": "_search_by_tavily"
    },
    {
        "name": "duckduckgo",
        "priority": 2,
        "requires_key": False,
        "env_var": None,
        "method": "_search_by_duckduckgo"
    },
    {
        "name": "baidu",
        "priority": 3,
        "requires_key": False,
        "env_var": None,
        "method": "_search_by_baidu"
    },
]


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
            
            # 级联搜索
            results = self._cascade_search(search_query, limit=10)
            
            if not results:
                logger.warning(f"所有搜索源均失败，使用默认结果")
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

    def _cascade_search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        级联搜索：按优先级尝试多个搜索源
        任何一个成功即返回，失败则尝试下一个
        """
        errors = []

        for provider in SEARCH_PROVIDER_REGISTRY:
            provider_name = provider["name"]
            method_name = provider["method"]
            requires_key = provider["requires_key"]
            env_var = provider["env_var"]

            # 检查API Key（如果需要）
            if requires_key:
                api_key = os.environ.get(env_var, "") if env_var else ""
                if not api_key:
                    logger.debug(f"[{provider_name}] 跳过：未配置 API Key")
                    continue

            logger.info(f"尝试搜索源: {provider_name}")

            try:
                # 调用对应的搜索方法
                results = getattr(self, method_name)(query, limit)
                
                if results:
                    logger.info(f"[{provider_name}] 搜索成功: {len(results)} 条结果")
                    return results
                else:
                    logger.warning(f"[{provider_name}] 返回空结果")
                    errors.append(f"{provider_name}: 空结果")
                    continue

            except Exception as e:
                err_str = str(e)
                logger.warning(f"[{provider_name}] 搜索失败: {err_str}")
                errors.append(f"{provider_name}: {err_str}")
                continue

        logger.error(f"所有搜索源均失败: {errors}")
        return []

    def _search_by_tavily(self, query: str, limit: int = 10) -> List[Dict]:
        """Tavily API 搜索"""
        import requests
        
        api_key = os.environ.get("TAVILY_API_KEY", "")
        if not api_key:
            raise ValueError("Tavily API Key 未配置")

        url = "https://api.tavily.com/search"
        headers = {"Content-Type": "application/json"}
        payload = {
            "query": query,
            "max_results": limit,
            "api_key": api_key
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        
        if resp.status_code == 401:
            raise ValueError("Tavily API Key 无效或已过期")
        elif resp.status_code == 429:
            # 限流，短暂等待后重试
            logger.warning("[tavily] 请求限流，等待2秒后重试...")
            time.sleep(2)
            resp = requests.post(url, json=payload, headers=headers, timeout=20)
        
        if resp.status_code != 200:
            raise ValueError(f"Tavily API 返回错误: HTTP {resp.status_code}")

        data = resp.json()
        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", "")
            })
        
        return results

    def _search_by_duckduckgo(self, query: str, limit: int = 10) -> List[Dict]:
        """DuckDuckGo HTML 搜索（无需 API Key）"""
        import requests
        from urllib.parse import quote

        # 使用 HTML 模式的 DuckDuckGo
        html_url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
        resp = requests.get(html_url, headers=headers, timeout=15)
        
        if resp.status_code != 200:
            raise ValueError(f"DuckDuckGo 返回错误: HTTP {resp.status_code}")

        # 解析 HTML 结果
        # 匹配 <a class="result__a" href="...">标题</a>
        pattern = r'<a class="result__a" href="([^"]+)"[^>]*>(.+?)</a>'
        matches = re.findall(pattern, resp.text)
        
        results = []
        for url, title_html in matches[:limit]:
            # 清理HTML标签
            title = re.sub(r'<[^>]+>', '', title_html).strip()
            if title:
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": ""
                })
        
        if not results:
            # 备用解析：尝试匹配其他格式
            alt_pattern = r'<a href="(https?://[^"]+)"[^>]*class="result__snippet"[^>]*>(.+?)</a>'
            alt_matches = re.findall(alt_pattern, resp.text)
            for url, snippet_html in alt_matches[:limit]:
                snippet = re.sub(r'<[^>]+>', '', snippet_html).strip()
                results.append({
                    "title": url.split('/')[-1][:50] or url,
                    "url": url,
                    "snippet": snippet
                })
        
        return results

    def _search_by_baidu(self, query: str, limit: int = 10) -> List[Dict]:
        """百度搜索（国内可用，无需 API Key）"""
        import requests
        from urllib.parse import quote

        # 百度搜索
        baidu_url = f"https://www.baidu.com/s?wd={quote(query)}&rn={limit}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        
        resp = requests.get(baidu_url, headers=headers, timeout=15)
        
        if resp.status_code != 200:
            raise ValueError(f"百度搜索返回错误: HTTP {resp.status_code}")
        
        # 解析百度搜索结果
        # 匹配 <h3 class="c-title"> 和 <a class="c-title">
        results = []
        
        # 方式1: 匹配标题和链接
        title_pattern = r'<a[^>]+class="[^"]*c-title[^"]*"[^>]+href="([^"]+)"[^>]*>(.+?)</a>'
        title_matches = re.findall(title_pattern, resp.text, re.DOTALL)
        
        for url, title_html in title_matches[:limit]:
            title = re.sub(r'<[^>]+>', '', title_html).strip()
            if title and url.startswith('http'):
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": ""
                })
        
        # 方式2: 备用解析
        if not results:
            # 匹配 <h3 class="c-title"><a href="...">标题</a></h3>
            h3_pattern = r'<h3[^>]*class="[^"]*c-title[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.+?)</a>'
            h3_matches = re.findall(h3_pattern, resp.text, re.DOTALL)
            for url, title_html in h3_matches[:limit]:
                title = re.sub(r'<[^>]+>', '', title_html).strip()
                if title:
                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": ""
                    })
        
        return results

    def _extract_related_topics(self, search_results: List[Dict]) -> List[str]:
        """从搜索结果中提取相关主题"""
        all_words = []
        
        for result in search_results:
            title = result.get("title", "")
            # 提取中文词（2字以上）
            chinese = re.findall(r'[\u4e00-\u9fff]{2,}', title)
            # 提取英文词（3字母以上）
            english = re.findall(r'[a-zA-Z]{3,}', title)
            all_words.extend(chinese)
            all_words.extend(english)
        
        # 统计词频
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
            
            # 如果有搜索结果，利用摘要生成更丰富的大纲
            summary = research_data.get("summary", "") if research_data else ""
            search_results = research_data.get("search_results", []) if research_data else []
            
            # 根据是否有内容决定大纲详细程度
            if summary and "暂无" not in summary:
                # 有真实搜索结果，生成更详细的大纲
                result = {
                    "title": f"深度解析：{topic}",
                    "sections": [
                        {
                            "name": "引言", 
                            "description": f"{topic}的背景与重要性", 
                            "key_points": ["背景介绍", "发展历程", "当前趋势"]
                        },
                        {
                            "name": "核心内容", 
                            "description": f"{topic}的关键要素", 
                            "key_points": ["要点1", "要点2", "要点3"]
                        },
                        {
                            "name": "实践方法", 
                            "description": f"如何应用{topic}", 
                            "key_points": ["方法步骤", "注意事项", "常见问题"]
                        },
                        {
                            "name": "结论", 
                            "description": "总结与建议", 
                            "key_points": ["核心总结", "未来展望", "行动建议"]
                        }
                    ],
                    "estimated_words": 3000
                }
            else:
                # 无搜索结果，使用简化大纲
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
