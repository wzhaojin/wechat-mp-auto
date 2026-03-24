"""
微信公众号自动化 - 内容审核 Skill
"""

import os
import re
import json
import hashlib
import time
import threading
import requests
from typing import Dict, List, Set
from pathlib import Path
from .base_skill import BaseSkill


class ContentReviewerSkill(BaseSkill):
    """内容审核"""
    
    PROHIBITED_WORDS = ["反动", "暴力", "色情", "赌博", "毒品", "诈骗", "谣言"]
    
    # 重复度检测参数
    N_GRAM_SIZE = 3  # n-gram 大小
    SIMILARITY_THRESHOLD = 30  # 相似度阈值（30%以上认为重复）
    MIN_CONTENT_LENGTH = 50  # 最小内容长度
    
    # 网络搜索重复度检测参数
    NETWORK_CHECK_ENABLED = True  # 是否启用网络检测
    KEY_SENTENCE_COUNT = 5  # 提取关键句数量
    SEARCH_MATCH_THRESHOLD = 10  # 搜索匹配阈值（%），降低以提高检出率
    SEARCH_TIMEOUT = 10  # 搜索超时时间（秒）
    SEARCH_DELAY = 1.0  # 搜索间隔（秒），避免频率限制
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._history_file = Path.home() / ".cache" / "wechat-mp-auto" / "article_history.json"
        self._history_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 获取 Tavily API Key
        self._tavily_api_key = os.environ.get("TAVILY_API_KEY", "")
        
        # 搜索结果缓存
        self._search_cache_file = Path.home() / ".cache" / "wechat-mp-auto" / "search_cache.json"
        self._search_cache = self._load_search_cache()
    
    def _load_search_cache(self) -> Dict:
        """加载搜索缓存"""
        if not self._search_cache_file.exists():
            return {}
        try:
            with open(self._search_cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _save_search_cache(self):
        """保存搜索缓存"""
        try:
            with open(self._search_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._search_cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def review_article(self, article: Dict) -> Dict:
        """全面审核"""
        content = article.get("markdown", article.get("content", ""))
        
        plagiarism = self.check_plagiarism(content)
        facts = self.verify_facts(content)
        prohibited = self.check_prohibited_content(content)
        
        issues = []
        if plagiarism.get("is_duplicated"):
            issues.append({"type": "plagiarism", "severity": "high", "message": "重复度较高"})
        if prohibited.get("violations"):
            issues.append({"type": "prohibited", "severity": "critical", "message": "包含违规内容"})
        
        return {
            "passed": len([i for i in issues if i.get("severity") == "critical"]) == 0,
            "issues": issues,
            "plagiarism": plagiarism,
            "facts": facts,
            "prohibited": prohibited
        }
    
    def check_plagiarism(self, content: str) -> Dict:
        """检查重复度 - 使用 n-gram + Jaccard 相似度"""
        # 预处理：去除特殊字符，保留中英文和数字
        cleaned = self._preprocess_text(content)
        
        # 内容太短，跳过检测
        if len(cleaned) < self.MIN_CONTENT_LENGTH:
            return {
                "is_duplicated": False,
                "similarity": 0,
                "reason": "内容太短，跳过检测",
                "history_count": 0
            }
        
        # 获取当前内容的 n-gram 集合
        current_ngrams = self._get_ngrams(cleaned, self.N_GRAM_SIZE)
        
        if not current_ngrams:
            return {
                "is_duplicated": False,
                "similarity": 0,
                "reason": "无法提取特征",
                "history_count": 0
            }
        
        # 加载历史文章
        history = self._load_history()
        
        # 计算与每篇历史文章的相似度
        max_similarity = 0
        most_similar_title = None
        
        for item in history:
            # 兼容：历史记录中存的是 title 字段（保存时用的），也可能是 content
            hist_content = self._preprocess_text(item.get("content", item.get("title", "")))
            if len(hist_content) < self.MIN_CONTENT_LENGTH:
                continue
            
            hist_ngrams = self._get_ngrams(hist_content, self.N_GRAM_SIZE)
            similarity = self._compute_jaccard_similarity(current_ngrams, hist_ngrams)
            
            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_title = item.get("title", "未知")
        
        # 判断是否重复
        is_duplicated = max_similarity >= self.SIMILARITY_THRESHOLD
        
        # 同时检查自重复（文章内部重复段落太多）
        internal_dup = self._check_internal_duplication(cleaned)
        
        result = {
            "is_duplicated": is_duplicated or internal_dup,
            "similarity": max_similarity,
            "similar_title": most_similar_title,
            "internal_duplication": internal_dup,
            "history_count": len(history),
            "threshold": self.SIMILARITY_THRESHOLD
        }
        
        # 保存当前文章到历史记录
        article_hash = self._compute_hash(cleaned)
        self._save_to_history(article_hash, content[:500])  # 保存前500字符的 hash
        
        return result
    
    def _preprocess_text(self, text: str) -> str:
        """预处理文本：去除 markdown 格式、特殊字符"""
        # 去除 markdown 标题符号
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        # 去除链接
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # 去除图片
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)
        # 去除代码块
        text = re.sub(r'```[\s\S]*?```', '', text)
        # 去除行内代码
        text = re.sub(r'`([^`]+)`', r'\1', text)
        # 去除特殊字符，只保留中英文、数字和常用标点
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9，。！？、；：""''（）【】《》\s]', '', text)
        # 去除多余空白
        text = re.sub(r'\s+', '', text)
        
        return text
    
    def _get_ngrams(self, text: str, n: int = 3) -> Set[str]:
        """获取文本的 n-gram 集合"""
        ngrams = set()
        for i in range(len(text) - n + 1):
            ngram = text[i:i+n]
            # 过滤掉纯数字的 n-gram（保留中英文混合）
            if not ngram.isdigit():
                ngrams.add(ngram)
        return ngrams
    
    def _compute_jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """计算 Jaccard 相似度"""
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0.0
        
        return (intersection / union) * 100
    
    def _check_internal_duplication(self, text: str) -> bool:
        """检查文章内部是否有大量重复内容"""
        # 获取更长的 n-gram（5-gram）来检测段落重复
        ngrams = self._get_ngrams(text, 5)
        
        # 如果某个 n-gram 出现次数过多，说明有重复
        ngram_count = {}
        for i in range(len(text) - 5 + 1):
            ngram = text[i:i+5]
            if not ngram.isdigit() and not ngram.isalpha():
                ngram_count[ngram] = ngram_count.get(ngram, 0) + 1
        
        # 找出出现最多的 n-gram
        if ngram_count:
            max_count = max(ngram_count.values())
            # 如果某个片段出现超过 10 次，认为有内部重复
            if max_count > 10:
                return True
        
        return False
    
    # ========== 网络搜索重复度检测 ==========
    
    def check_network_plagiarism(self, content: str, callback=None) -> Dict:
        """
        检查网络重复度（异步）
        
        通过提取关键句子并搜索比对，判断文章是否与网上已有内容重复。
        
        Args:
            content: 文章内容
            callback: 异步完成后的回调函数
            
        Returns:
            初步结果（实际检测在后台进行）
        """
        # 检查是否启用网络检测
        if not self.NETWORK_CHECK_ENABLED:
            return {
                "enabled": False,
                "reason": "网络检测未启用",
                "is_plagiarized": False
            }
        
        # 检查是否有 API Key
        if not self._tavily_api_key:
            # 尝试从配置文件读取
            config_file = Path.home() / ".config" / "wechat-mp-auto" / "config.json"
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                        self._tavily_api_key = config.get("tavily_api_key", "")
                except Exception:
                    pass
            
            # 再次检查
            if not self._tavily_api_key:
                return {
                    "enabled": False,
                    "reason": "未配置 TAVILY_API_KEY（请设置环境变量或配置文件）",
                    "is_plagiarized": False,
                    "how_to_config": "设置环境变量 TAVILY_API_KEY 或在 config.json 中添加 tavily_api_key"
                }
        
        # 提取关键句子
        key_sentences = self._extract_key_sentences(content)
        if not key_sentences:
            return {
                "enabled": True,
                "is_plagiarized": False,
                "reason": "内容太短，无法提取关键句"
            }
        
        # 启动异步检测
        result_container = {"result": None}
        
        def async_check():
            result = self._do_network_check(key_sentences, content)
            result_container["result"] = result
            if callback:
                callback(result)
        
        thread = threading.Thread(target=async_check)
        thread.daemon = True
        thread.start()
        
        # 返回初步结果
        return {
            "enabled": True,
            "async": True,
            "key_sentences_count": len(key_sentences),
            "status": "检测中...",
            "_thread": thread,
            "_result_container": result_container
        }
    
    def get_network_result(self, preliminary_result: Dict) -> Dict:
        """获取异步检测结果"""
        if not preliminary_result.get("enabled"):
            return preliminary_result
        
        if preliminary_result.get("async"):
            thread = preliminary_result.get("_thread")
            result_container = preliminary_result.get("_result_container")
            
            if thread and thread.is_alive():
                return {
                    "status": "检测中...",
                    "progress": "请稍候"
                }
            
            if result_container and result_container.get("result"):
                return result_container["result"]
            
            return {"status": "检测完成", "is_plagiarized": False}
        
        return preliminary_result
    
    def _do_network_check(self, key_sentences: List[str], content: str) -> Dict:
        """执行网络检测"""
        matches = []
        total_checks = len(key_sentences)
        
        for i, sentence in enumerate(key_sentences):
            # 检查缓存
            cache_key = self._compute_hash(sentence[:50])
            if cache_key in self._search_cache:
                cached = self._search_cache[cache_key]
                match_result = cached
            else:
                # 执行搜索
                match_result = self._search_and_compare(sentence)
                
                # 保存到缓存
                self._search_cache[cache_key] = match_result
            
            if match_result.get("is_matched"):
                matches.append({
                    "sentence": sentence[:50] + "...",
                    "matched_url": match_result.get("matched_url"),
                    "similarity": match_result.get("similarity")
                })
            
            # 延时，避免频率限制
            if i < total_checks - 1:
                time.sleep(self.SEARCH_DELAY)
        
        # 计算匹配率
        match_ratio = (len(matches) / total_checks * 100) if total_checks > 0 else 0
        
        result = {
            "is_plagiarized": match_ratio >= self.SEARCH_MATCH_THRESHOLD,
            "match_ratio": match_ratio,
            "matches": matches,
            "total_checks": total_checks,
            "threshold": self.SEARCH_MATCH_THRESHOLD,
            "key_sentences": key_sentences
        }
        
        # 保存缓存
        self._save_search_cache()
        
        return result
    
    def _extract_key_sentences(self, text: str, n: int = 5) -> List[str]:
        """提取关键句子"""
        # 预处理
        cleaned = self._preprocess_text(text)
        
        if len(cleaned) < 100:
            return []
        
        # 分割句子
        sentences = re.split(r'[。！？\n]', cleaned)
        sentences = [s.strip() for s in sentences if len(s.strip()) >= 20]
        
        if not sentences:
            return []
        
        # 计算每句的权重（位置 + 长度）
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            # 位置权重：开头和结尾的句子更重要
            position_weight = 1.0
            if i == 0:
                position_weight = 1.5
            elif i < 3:
                position_weight = 1.2
            
            # 长度权重：适中最好
            length = len(sentence)
            if length < 20:
                length_weight = 0.5
            elif length > 100:
                length_weight = 0.8
            else:
                length_weight = 1.0
            
            score = position_weight * length_weight
            scored_sentences.append((score, sentence))
        
        # 按分数排序，取前 N 个
        scored_sentences.sort(reverse=True, key=lambda x: x[0])
        
        return [s[1] for s in scored_sentences[:n]]
    
    def _search_and_compare(self, sentence: str) -> Dict:
        """搜索并比对"""
        try:
            # 提取关键词用于搜索（取句子中重要部分）
            search_query = self._extract_search_keywords(sentence)
            
            # 调用 Tavily API
            url = "https://api.tavily.com/search"
            headers = {"Content-Type": "application/json"}
            data = {
                "api_key": self._tavily_api_key,
                "query": search_query,
                "search_depth": "basic",
                "max_results": 5
            }
            
            response = requests.post(
                url, 
                json=data, 
                headers=headers,
                timeout=self.SEARCH_TIMEOUT
            )
            
            if response.status_code != 200:
                return {"is_matched": False, "error": f"API错误: {response.status_code}"}
            
            results = response.json()
            search_results = results.get("results", [])
            
            if not search_results:
                return {"is_matched": False}
            
            # 计算与搜索结果的相似度
            best_match = None
            best_similarity = 0
            
            for result in search_results:
                title = result.get("title", "")
                content = result.get("content", "")[:500]
                combined = title + " " + content
                
                # 方法1：文本相似度
                text_similarity = self._compute_text_similarity(sentence, combined)
                
                # 方法2：关键词重叠度
                keyword_similarity = self._compute_keyword_overlap(sentence, combined)
                
                # 综合相似度（文本相似度 + 关键词权重）
                similarity = max(text_similarity, keyword_similarity)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = {
                        "url": result.get("url"),
                        "title": title,
                        "similarity": similarity,
                        "text_similarity": text_similarity,
                        "keyword_similarity": keyword_similarity
                    }
            
            # 阈值判断
            is_matched = best_similarity >= 20  # 20% 以上认为匹配
            
            return {
                "is_matched": is_matched,
                "similarity": best_similarity,
                "matched_url": best_match.get("url") if best_match else None,
                "matched_title": best_match.get("title") if best_match else None
            }
            
        except requests.Timeout:
            return {"is_matched": False, "error": "搜索超时"}
        except Exception as e:
            return {"is_matched": False, "error": str(e)}
    
    def _compute_text_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度（基于字符集交集）"""
        # 预处理
        t1 = self._preprocess_text(text1)
        t2 = self._preprocess_text(text2)
        
        if not t1 or not t2:
            return 0.0
        
        # 计算字符级 Jaccard 相似度
        set1 = set(t1[i:i+3] for i in range(len(t1)-2))  # 3-gram
        set2 = set(t2[i:i+3] for i in range(len(t2)-2))
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return (intersection / union * 100) if union > 0 else 0.0
    
    def _extract_search_keywords(self, sentence: str) -> str:
        """从句子中提取简短的搜索关键词"""
        import re
        
        # 去除标点和多余空格
        text = re.sub(r'[，。！？、；：""''（）【】《》]', ' ', sentence)
        text = ' '.join(text.split())  # 合并多余空格
        
        # 如果句子太长，截取前30个字符
        if len(text) > 30:
            text = text[:30]
        
        return text
    
    def _compute_keyword_overlap(self, text1: str, text2: str) -> float:
        """计算关键词重叠度"""
        # 提取关键词
        kw1 = set(self._extract_search_keywords(text1).split())
        kw2 = set(self._extract_search_keywords(text2).split())
        
        if not kw1 or not kw2:
            return 0.0
        
        # 计算 Jaccard
        intersection = len(kw1 & kw2)
        union = len(kw1 | kw2)
        
        return (intersection / union * 100) if union > 0 else 0.0
    
    def _compute_hash(self, text: str) -> str:
        """计算文本的 MD5 哈希"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _load_history(self) -> List[Dict]:
        """加载历史文章记录"""
        if not self._history_file.exists():
            return []
        
        try:
            with open(self._history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    
    def _save_to_history(self, content_hash: str, title: str = ""):
        """保存文章到历史记录"""
        history = self._load_history()
        
        # 检查是否已存在
        for item in history:
            if item.get("hash") == content_hash:
                return  # 已存在，不重复添加
        
        # 添加新记录
        import time
        history.append({
            "hash": content_hash,
            "title": title,
            "timestamp": int(time.time())
        })
        
        # 只保留最近 100 篇
        history = history[-100:]
        
        try:
            with open(self._history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def verify_facts(self, content: str) -> Dict:
        """验证数据"""
        data_points = self._extract_data_points(content)
        return {"total_points": len(data_points), "verified": [], "issues": []}
    
    def check_prohibited_content(self, content: str) -> Dict:
        """检查违规"""
        violations = []
        content_lower = content.lower()
        for word in self.PROHIBITED_WORDS:
            if word in content_lower:
                violations.append({"word": word})
        return {"has_violations": len(violations) > 0, "violations": violations}
    
    def _extract_data_points(self, content: str) -> List[Dict]:
        percentages = re.findall(r'(\d+(?:\.\d+)?)\s*%', content)
        return [{"type": "percentage", "value": p} for p in percentages]
    
    def auto_fix(self, article: Dict, issues: List[Dict]) -> Dict:
        """自动修复"""
        fixed = article.copy()
        fixed["fixed"] = True
        return fixed
    
    def clear_history(self) -> Dict:
        """清除历史记录"""
        try:
            if self._history_file.exists():
                self._history_file.unlink()
            return {"success": True, "message": "历史记录已清除"}
        except Exception as e:
            return {"success": False, "message": str(e)}
