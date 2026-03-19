"""
微信公众号自动化 - 数据分析 Skill
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from .base_skill import BaseSkill


class AnalyticsSkill(BaseSkill):
    """数据分析"""
    
    def get_article_stats(self, begin_date: str, end_date: Optional[str] = None) -> Dict:
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        data = {"begin_date": begin_date.replace("-", ""), "end_date": end_date.replace("-", "")}
        result = self.post("/cgi-bin/analysis/get_article_summary", data)
        
        articles = result.get("list", [])
        stats = []
        for a in articles:
            stats.append({
                "title": a.get("title", ""),
                "read_count": a.get("read_count", 0),
                "like_count": a.get("like_count", 0),
                "share_count": a.get("share_count", 0)
            })
        
        return {"begin_date": begin_date, "end_date": end_date, "articles": stats}
    
    def get_user_stats(self, begin_date: str, end_date: Optional[str] = None) -> Dict:
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        data = {"begin_date": begin_date.replace("-", ""), "end_date": end_date.replace("-", "")}
        result = self.post("/cgi-bin/analysis/get_user_summary", data)
        
        return {"begin_date": begin_date, "end_date": end_date, "users": result.get("list", [])}
    
    def get_article_ranking(self, begin_date: str, end_date: Optional[str] = None, limit: int = 10) -> List[Dict]:
        stats = self.get_article_stats(begin_date, end_date)
        articles = stats.get("articles", [])
        sorted_articles = sorted(articles, key=lambda x: x.get("read_count", 0), reverse=True)
        return sorted_articles[:limit]
    
    def generate_report(self, stats: Dict) -> str:
        articles = stats.get("articles", [])
        if not articles:
            return "暂无数据"
        
        total_read = sum(a.get("read_count", 0) for a in articles)
        total_like = sum(a.get("like_count", 0) for a in articles)
        
        return f"""
📊 数据报告
━━━━━━━━━━━━━━━
文章数: {len(articles)}
总阅读: {total_read:,}
总点赞: {total_like:,}
平均阅读: {total_read // len(articles) if articles else 0:,}
"""
    
    def track_article(self, media_id: str, days: int = 7) -> Dict:
        end_date = datetime.now()
        begin_date = end_date - timedelta(days=days)
        stats = self.get_article_stats(begin_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        return {"media_id": media_id, "stats": stats, "report": self.generate_report(stats)}
