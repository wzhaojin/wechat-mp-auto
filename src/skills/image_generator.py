"""
微信公众号自动化 - 配图生成 Skill

封面和插图来源：
1. AI 生成（需配置 AI API）
2. Pexels/Unsplash 无版权图片
"""

import os
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Optional
from .base_skill import BaseSkill

# 配置日志
logger = logging.getLogger(__name__)


class ImageGeneratorSkill(BaseSkill):
    """配图生成 - 支持 AI + Pexels + Unsplash"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache_dir = Path.home() / ".cache" / "wechat-mp-auto" / "images"
        
        # 安全检查：确保缓存目录创建在安全路径
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"创建缓存目录失败: {str(e)}")
            raise

        # 读取 API Keys - 从环境变量读取，不记录日志
        self._pexels_api_key = os.environ.get("PEXELS_API_KEY", "")
        self._unsplash_api_key = os.environ.get("UNSPLASH_API_KEY", "")
        self._openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        
        # 记录已配置的API来源（不记录具体key）
        api_sources = []
        if self._pexels_api_key:
            api_sources.append("Pexels")
        if self._unsplash_api_key:
            api_sources.append("Unsplash")
        if self._openai_api_key:
            api_sources.append("OpenAI")
        logger.info(f"图片生成API来源: {api_sources if api_sources else '无'}")

    def generate_cover(self, title: str, keywords: List[str]) -> str:
        """生成封面图"""
        # 参数验证
        if not title or not isinstance(title, str):
            logger.error("无效的title参数: title不能为空且必须是字符串")
            raise ValueError("title不能为空且必须是字符串")
        
        if keywords is not None:
            if not isinstance(keywords, list):
                logger.error("无效的keywords参数: keywords必须是列表")
                raise ValueError("keywords必须是列表")
            if len(keywords) > 10:
                logger.warning(f"关键词数量过多({len(keywords)}),将限制为前10个")
                keywords = keywords[:10]

        try:
            logger.info(f"开始生成封面图: {title[:50]}...")
            
            cover_keywords = self._extract_cover_keywords(title, keywords)

            # 1. 优先 AI 生成
            if self._openai_api_key:
                img_path = self._generate_by_ai(title, "cover")
                if img_path:
                    logger.info(f"AI生成封面图成功: {img_path}")
                    return img_path

            # 2. 其次 Pexels/Unsplash
            images = self._search_all(cover_keywords)
            if images:
                img_path = self._download_image(images[0], "cover")
                if img_path:
                    logger.info(f"图库下载封面图成功: {img_path}")
                    return img_path
            
            logger.warning(f"未能生成封面图: {title[:50]}...")
            return None
        except Exception as e:
            logger.error(f"生成封面图失败: {str(e)}", exc_info=True)
            raise

    def generate_illustration(self, section: str, keywords: List[str]) -> str:
        """生成插图"""
        # 参数验证
        if not section or not isinstance(section, str):
            logger.error("无效的section参数: section不能为空且必须是字符串")
            raise ValueError("section不能为空且必须是字符串")
        
        if keywords is not None:
            if not isinstance(keywords, list):
                logger.error("无效的keywords参数: keywords必须是列表")
                raise ValueError("keywords必须是列表")

        try:
            logger.info(f"开始生成插图: {section[:50]}...")
            
            illust_keywords = self._extract_illustration_keywords(section, keywords)

            # 1. 优先 AI 生成
            if self._openai_api_key:
                img_path = self._generate_by_ai(section, "illustration")
                if img_path:
                    logger.info(f"AI生成插图成功: {img_path}")
                    return img_path

            # 2. 其次 Pexels/Unsplash
            images = self._search_all(illust_keywords)
            if images:
                img_path = self._download_image(images[0], "illustration")
                if img_path:
                    logger.info(f"图库下载插图成功: {img_path}")
                    return img_path
            
            logger.warning(f"未能生成插图: {section[:50]}...")
            return None
        except Exception as e:
            logger.error(f"生成插图失败: {str(e)}", exc_info=True)
            raise

    def _generate_by_ai(self, prompt: str, img_type: str) -> Optional[str]:
        """通过 AI 生成图片 - 支持 DALL-E 和多种 API"""
        # 安全检查：确保至少有一个 API key
        if not self._openai_api_key and not self._pexels_api_key and not self._unsplash_api_key:
            logger.warning("未配置任何图片生成 API")
            return None

        # 确定图片尺寸
        size = "1792x1024" if img_type == "cover" else "1024x1024"
        
        # 构建 prompt
        full_prompt = self._build_ai_prompt(prompt, img_type)
        
        # 尝试 OpenAI DALL-E
        if self._openai_api_key:
            result = self._generate_dalle(full_prompt, size)
            if result:
                return result
        
        logger.warning("AI 图片生成失败")
        return None
    
    def _build_ai_prompt(self, prompt: str, img_type: str) -> str:
        """构建 AI 生成的 prompt"""
        # 微信公众号配图风格指导
        style_guide = (
            "微信公众号文章配图，简约现代风格，"
            "清新配色，专业商务感，适合文章内容可视化。"
        )
        
        if img_type == "cover":
            return f"{prompt}，{style_guide}，横版图片 16:9 比例，高清摄影风格"
        else:
            return f"{prompt}，{style_guide}，方形图片 1:1 比例，插画风格"
    
    def _generate_dalle(self, prompt: str, size: str = "1024x1024") -> Optional[str]:
        """调用 OpenAI DALL-E 生成图片"""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self._openai_api_key)
            
            logger.info(f"正在调用 DALL-E 生成图片: {size}")
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            logger.info(f"DALL-E 生成成功，下载图片...")
            
            # 下载图片
            return self._download_from_url(image_url, "dalle")
            
        except ImportError:
            logger.error("openai 库未安装: pip install openai")
        except Exception as e:
            logger.error(f"DALL-E 生成失败: {str(e)}")
        
        return None
    
    def _download_from_url(self, url: str, prefix: str = "ai") -> Optional[str]:
        """从 URL 下载图片"""
        try:
            import requests
            
            filename = f"{prefix}_{uuid.uuid4().hex[:8]}.jpg"
            filepath = self._cache_dir / filename
            
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                logger.info(f"AI 图片下载成功: {filepath}")
                return str(filepath)
            else:
                logger.warning(f"AI 图片下载失败 HTTP {resp.status_code}")
        except Exception as e:
            logger.error(f"下载 AI 图片失败: {str(e)}")
        
        return None
    
    def generate_by_text(self, text: str, img_type: str = "illustration") -> Optional[str]:
        """
        公开接口：根据文本生成配图
        用于在文章中根据段落内容自动生成插图
        """
        if not text or not isinstance(text, str):
            logger.error("无效的 text 参数")
            return None
        
        # 提取关键词
        keywords = self._extract_illustration_keywords(text, [])
        
        # 优先 AI 生成
        if self._openai_api_key:
            img_path = self._generate_by_ai(keywords, img_type)
            if img_path:
                logger.info(f"文本配图生成成功: {text[:30]}...")
                return img_path
        
        # 备选图库
        images = self._search_all(keywords, 3)
        if images:
            img_path = self._download_image(images[0], "text_illust")
            if img_path:
                logger.info(f"文本配图（图库）生成成功: {text[:30]}...")
                return img_path
        
        logger.warning(f"文本配图生成失败: {text[:30]}...")
        return None

    def _search_all(self, keywords: str, count: int = 5) -> List[Dict]:
        """双 API 搜索，自动切换"""
        # 参数验证
        if not keywords or not isinstance(keywords, str):
            logger.warning(f"无效的搜索关键词: {keywords}")
            return []
        
        if not isinstance(count, int) or count < 1 or count > 30:
            logger.warning(f"无效的count参数: {count}, 使用默认值5")
            count = 5

        try:
            # 优先 Pexels
            if self._pexels_api_key:
                images = self._search_pexels(keywords, count)
                if images:
                    logger.debug(f"Pexels搜索成功，找到 {len(images)} 张图片")
                    return images

            # 备选 Unsplash
            if self._unsplash_api_key:
                images = self._search_unsplash(keywords, count)
                if images:
                    logger.debug(f"Unsplash搜索成功，找到 {len(images)} 张图片")
                    return images

            logger.warning(f"所有图库搜索均未返回结果: {keywords}")
            return []
        except Exception as e:
            logger.error(f"图片搜索失败: {str(e)}", exc_info=True)
            return []

    def _search_pexels(self, keywords: str, count: int = 5) -> List[Dict]:
        """搜索 Pexels"""
        if not self._pexels_api_key:
            return []
        
        try:
            import requests
            
            url = f"https://api.pexels.com/v1/search?query={keywords}&per_page={count}"
            headers = {"Authorization": self._pexels_api_key}
            
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"Pexels API返回错误状态码: {resp.status_code}")
                return []
            
            data = resp.json()
            photos = data.get("photos", [])
            
            return [
                {
                    "url": p.get("src", {}).get("original"),
                    "thumb_url": p.get("src", {}).get("medium"),
                    "author": p.get("photographer", "Unknown"),
                    "source": "Pexels"
                }
                for p in photos
            ]
        except ImportError:
            logger.error("requests库未安装")
            return []
        except Exception as e:
            logger.error(f"Pexels搜索失败: {str(e)}")
            return []

    def _search_unsplash(self, keywords: str, count: int = 5) -> List[Dict]:
        """搜索 Unsplash"""
        if not self._unsplash_api_key:
            return []
        
        try:
            import requests
            
            url = f"https://api.unsplash.com/search/photos?query={keywords}&per_page={count}"
            headers = {"Authorization": f"Client-ID {self._unsplash_api_key}"}
            
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"Unsplash API返回错误状态码: {resp.status_code}")
                return []
            
            data = resp.json()
            results = data.get("results", [])
            
            return [
                {
                    "url": r.get("urls", {}).get("regular"),
                    "thumb_url": r.get("urls", {}).get("thumb"),
                    "author": r.get("user", {}).get("name", "Unknown"),
                    "source": "Unsplash"
                }
                for r in results
            ]
        except ImportError:
            logger.error("requests库未安装")
            return []
        except Exception as e:
            logger.error(f"Unsplash搜索失败: {str(e)}")
            return []

    def _download_image(self, image_info: Dict, prefix: str) -> Optional[str]:
        """下载图片"""
        # 参数验证
        if not image_info or not isinstance(image_info, dict):
            logger.error("无效的image_info参数")
            return None
        
        url = image_info.get("url", "")
        if not url:
            logger.error("图片URL为空")
            return None

        # 安全检查：验证URL来源
        allowed_domains = ["images.pexels.com", "unsplash.com", "plus.unsplash.com"]
        if not any(domain in url for domain in allowed_domains):
            logger.warning(f"图片URL不在允许的域名范围内: {url[:50]}...")
            return None

        try:
            import requests
            
            filename = f"{prefix}_{uuid.uuid4().hex[:8]}.jpg"
            filepath = self._cache_dir / filename
            
            # 安全检查：确保文件路径在缓存目录内
            if ".." in str(filepath) or str(filepath).startswith("/"):
                # 规范化路径并验证
                filepath = filepath.resolve()
                if not str(filepath).startswith(str(self._cache_dir.resolve())):
                    logger.error(f"不安全的文件路径: {filepath}")
                    return None
            
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                logger.info(f"图片下载成功: {filepath}")
                return str(filepath)
            else:
                logger.warning(f"图片下载失败HTTP {resp.status_code}: {url[:50]}...")
        except ImportError:
            logger.error("requests库未安装")
            return None
        except Exception as e:
            logger.error(f"图片下载失败: {str(e)}")
            return None

        return None

    def _extract_cover_keywords(self, title: str, keywords: List[str]) -> str:
        """提取封面关键词"""
        if not title:
            return ""
        return " ".join(title.split()[:3] + (keywords[:3] if keywords else []))

    def _extract_illustration_keywords(self, section: str, keywords: List[str]) -> str:
        """提取插图关键词"""
        if not section:
            return ""
        return " ".join(section.split()[:3])

    def batch_generate(self, title: str, sections: List[str], keywords: List[str]) -> Dict:
        """批量生成图片"""
        # 参数验证
        if not title or not isinstance(title, str):
            logger.error("无效的title参数")
            raise ValueError("title不能为空且必须是字符串")
        
        if not sections or not isinstance(sections, list):
            logger.error("无效的sections参数")
            raise ValueError("sections不能为空且必须是列表")
        
        if len(sections) > 50:
            logger.warning(f"章节数量过多({len(sections)}),将限制为前50个")
            sections = sections[:50]

        try:
            logger.info(f"开始批量生成图片: {title[:50]}..., 共 {len(sections)} 个章节")
            
            result = {"cover": None, "illustrations": []}
            result["cover"] = self.generate_cover(title, keywords)
            
            for section in sections:
                try:
                    illust = self.generate_illustration(section, keywords)
                    if illust:
                        result["illustrations"].append(illust)
                except Exception as e:
                    logger.warning(f"生成章节插图失败: {section[:30]}... - {str(e)}")
                    continue
            
            logger.info(f"批量生成完成: 封面={result['cover'] is not None}, 插图={len(result['illustrations'])}张")
            return result
        except Exception as e:
            logger.error(f"批量生成图片失败: {str(e)}", exc_info=True)
            raise
