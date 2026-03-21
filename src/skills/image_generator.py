"""
微信公众号自动化 - 配图生成 Skill

图片来源：
1. AI 生图（用户选择模型后调用）
2. Pexels/Unsplash 图库检索
"""

import os
import uuid
import time
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from .base_skill import BaseSkill
from config import Config

# 配置日志
logger = logging.getLogger(__name__)

# 缓存路径和TTL
CACHE_FILE = Path.home() / ".cache" / "wechat-mp-auto" / "image_models_cache.json"
CACHE_TTL = 24 * 3600  # 24小时

# 常用生图模型注册表（按 provider 分组）
# 每个条目包含：图像生成 API 路径、认证方式、请求格式
IMAGE_GEN_PROVIDER_MAP = {
    # === 国内 ===
    "ali-bailian": {
        "image_api_path": "/services/aigc/text2image/image-synthesis",
        "model": "wanx2.1",
        "auth_type": "bearer",
        "req_format": "wanx",
        "display_name": "通义万图（wanx2.1）",
    },
    "minimax-cn": {
        "image_api_path": "/images/generations",
        "model": "image-01",
        "auth_type": "bearer",
        "req_format": "openai_like",
        "display_name": "MiniMax Image-01",
    },
    "baidu": {
        "image_api_path": "/rest/2.0/ernie-vilg/v2/text2image",
        "model": "ernie-vilg-v2",
        "auth_type": "bearer",
        "req_format": "baidu",
        "display_name": "百度文心一格",
    },
    "tencent": {
        "image_api_path": "/hunyuan/v1/ai_image",
        "model": "hunyuan-image",
        "auth_type": "hmac_sha1",
        "req_format": "tencent",
        "display_name": "腾讯混元",
    },
    "sensetime": {
        "image_api_path": "/v1/visionprotect/risenlp/nlpcg/diffusion",
        "model": "nova-smooth",
        "auth_type": "bearer",
        "req_format": "openai_like",
        "display_name": "商汤（nova-smooth）",
    },
    "bytedance": {
        "image_api_path": "/cv/sdxl/txt2img",
        "model": "sdxl-txt2img",
        "auth_type": "bearer",
        "req_format": "openai_like",
        "display_name": "字节豆包（SDXL）",
    },
    "zhipu": {
        "image_api_path": "/api/paulgraham/t2i",
        "model": "cogview-4",
        "auth_type": "bearer",
        "req_format": "openai_like",
        "display_name": "智谱 CogView-4",
    },
    # === 国外 ===
    "openai": {
        "image_api_path": "/v1/images/generations",
        "model": "dall-e-3",
        "auth_type": "bearer",
        "req_format": "openai_dalle",
        "display_name": "OpenAI DALL-E 3",
    },
    "google": {
        "image_api_path": "/publishers/google/models/imagen-3/image:predict",
        "model": "imagen-3",
        "auth_type": "bearer",
        "req_format": "google_imagen",
        "display_name": "Google Imagen 3",
    },
    "stability-ai": {
        "image_api_path": "/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
        "model": "stable-diffusion-xl-1024-v1-0",
        "auth_type": "bearer",
        "req_format": "sd_api",
        "display_name": "Stability AI SDXL",
    },
    "replicate": {
        "image_api_path": "/v1/predictions",
        "model": "flux-schnell",
        "auth_type": "bearer",
        "req_format": "replicate",
        "display_name": "Replicate Flux",
    },
    "aws-bedrock": {
        "image_api_path": "/imagegeneration/stabilityai",
        "model": "stability.stable-diffusion-xl-v1",
        "auth_type": "aws_sigv4",
        "req_format": "aws_bedrock",
        "display_name": "AWS Bedrock SDXL",
    },
    "azure-openai": {
        "image_api_path": "/openai/deployments/dall-e-3/images/generations?api-version=2024-02-01",
        "model": "dall-e-3",
        "auth_type": "api_key",
        "req_format": "azure_dalle",
        "display_name": "Azure OpenAI DALL-E 3",
    },
}

# 不支持生图的知名模型（仅作说明，不会被添加到列表）
# - anthropic/claude 系列：纯文本+视觉理解，无生图API
# - openai/gpt-4o / gpt-4-turbo：视觉模型但无生图API


class ImageGeneratorSkill(BaseSkill):
    """配图生成 - 支持 AI 生图 + Pexels/Unsplash 图库"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache_dir = Path.home() / ".cache" / "wechat-mp-auto" / "images"

        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"创建缓存目录失败: {str(e)}")
            raise

        self._pexels_api_key = os.environ.get("PEXELS_API_KEY", "")
        self._unsplash_api_key = os.environ.get("UNSPLASH_API_KEY", "")
        self._config = Config()

        prefs = self._config.get_image_preferences()
        self._image_source = prefs.get("image_source")
        self._ai_model = prefs.get("ai_model")

        logger.info(f"图片来源偏好: {self._image_source}, AI模型偏好: {self._ai_model}")

    # ==================== 引导与选择 ====================

    def get_image_source_options(self) -> Dict:
        """
        返回图片来源选择提示信息。
        供调用方引导用户选择图片来源。
        """
        has_pexels = bool(self._pexels_api_key)
        has_unsplash = bool(self._unsplash_api_key)

        search_desc = "从 Pexels/Unsplash 图库搜索免费图片"
        if not has_pexels and not has_unsplash:
            search_desc = "需配置 PEXELS_API_KEY 和/或 UNSPLASH_API_KEY 环境变量"

        return {
            "need_user_choice": True,
            "choice_type": "image_source",
            "message": "请选择封面图和插图的图片来源",
            "options": [
                {
                    "id": "ai",
                    "name": "AI生图",
                    "description": "调用AI模型生成图片"
                },
                {
                    "id": "search",
                    "name": "图片接口检索",
                    "description": search_desc,
                    "disabled": not (has_pexels or has_unsplash)
                }
            ]
        }

    def _read_cache(self) -> Optional[List[Dict]]:
        """从缓存读取已探测的生图模型列表"""
        if not CACHE_FILE.exists():
            return None
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            ts = data.get("ts", 0)
            if time.time() - ts < CACHE_TTL:
                models = data.get("models", [])
                logger.info(f"从缓存读取到 {len(models)} 个已探测的生图模型")
                return models
            else:
                logger.debug("缓存已过期，需要重新探测")
        except Exception as e:
            logger.warning(f"读取生图模型缓存失败: {e}")
        return None

    def _write_cache(self, models: List[Dict]):
        """将探测结果写入缓存"""
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({"ts": time.time(), "models": models}, f, ensure_ascii=False, indent=2)
            logger.debug(f"已写入缓存: {len(models)} 个生图模型")
        except Exception as e:
            logger.warning(f"写入生图模型缓存失败: {e}")

    def _prefilter_models(self) -> List[Dict]:
        """
        初筛：从 OpenClaw 配置中读取所有模型，
        过滤出可能是生图模型的候选（input含image 或 api含image）。
        """
        candidates = []
        try:
            config_file = Path.home() / ".openclaw" / "openclaw.json"
            if not config_file.exists():
                logger.warning("未找到 OpenClaw 配置文件")
                return []

            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            providers = data.get("models", {}).get("providers", {})
            for provider, cfg in providers.items():
                api_type = cfg.get("api", "")
                base_url = cfg.get("baseUrl", "")

                # 只处理注册表中存在的 provider
                if provider not in IMAGE_GEN_PROVIDER_MAP:
                    continue

                for m in cfg.get("models", []):
                    model_id = m.get("id", "")
                    model_name = m.get("name", model_id)
                    inputs = m.get("input", [])

                    # 初筛条件：input 包含 "image" 或 api 类型包含 "image"
                    is_candidate = (
                        ("image" in inputs) or
                        ("image" in api_type.lower())
                    )

                    if is_candidate:
                        candidates.append({
                            "id": model_id,
                            "name": model_name,
                            "provider": provider,
                            "base_url": base_url,
                        })
                        logger.debug(f"初筛候选生图模型: {provider}/{model_id}")

            logger.info(f"初筛出 {len(candidates)} 个候选生图模型")
        except Exception as e:
            logger.error(f"读取 OpenClaw 模型配置失败: {e}")

        return candidates

    def _get_credential(self, model_id: str) -> Optional[Dict]:
        """根据模型 ID 从 OpenClaw 配置获取 provider 的 API 凭证"""
        try:
            import json
            # 读 credentials
            cred_file = Path.home() / ".openclaw" / "credentials" / "api-keys.json"
            if cred_file.exists():
                with open(cred_file) as f:
                    creds = json.load(f)

            # 读 model 配置，找 provider
            config_file = Path.home() / ".openclaw" / "openclaw.json"
            if config_file.exists():
                with open(config_file) as f:
                    config = json.load(f)
                providers = config.get("models", {}).get("providers", {})
                for pname, pcfg in providers.items():
                    for m in pcfg.get("models", []):
                        if m.get("id") == model_id:
                            api_key = creds.get(pname, {}).get("apiKey", "")
                            return {
                                "provider": pname,
                                "apiKey": api_key,
                                "baseUrl": pcfg.get("baseUrl", ""),
                            }
        except Exception as e:
            logger.warning(f"读取 OpenClaw 凭证失败: {e}")
        return None

    def _build_probe_request(self, provider: str, req_format: str) -> Dict:
        """构造探测请求（最小化 prompt，低分辨率）"""
        prompt = "a simple red circle"  # 最简 prompt
        size = "512x512"

        if req_format == "openai_dalle":
            return {"model": "dall-e-3", "prompt": prompt, "n": 1, "size": "1024x1024"}
        elif req_format == "google_imagen":
            return {"prompt": prompt, "image_size": {"height": 512, "width": 512}, "sample_count": 1}
        elif req_format == "wanx":
            return {"model": "wanx2.1", "input": {"prompt": prompt}, "parameters": {"size": size, "n": 1}}
        elif req_format == "sd_api":
            return {"text_prompts": [{"text": prompt}], "cfg_scale": 7.5, "height": 512, "width": 512}
        elif req_format == "replicate":
            # flux-schnell 的探测格式
            return {"version": "acl IpShpGBJlsNMENjkEZJDlFNMJAEqSby", "input": {"prompt": prompt, "num_outputs": 1}}
        elif req_format == "baidu":
            return {"text": prompt, "image_size": "512*512", "style": "adv_flat"}
        elif req_format == "tencent":
            return {"prompt": prompt, "width": 512, "height": 512, "version": "v1.5"}
        elif req_format == "azure_dalle":
            return {"prompt": prompt, "n": 1, "size": "1024x1024"}
        elif req_format == "aws_bedrock":
            return {"text_prompts": [{"text": prompt}], "cfg_scale": 7.5, "height": 512, "width": 512}
        else:
            # 默认 OpenAI 兼容格式
            return {"model": "image-01", "prompt": prompt, "n": 1, "size": size}

    def _parse_probe_response(self, provider: str, req_format: str, resp_data: Dict) -> Optional[str]:
        """解析探测响应，提取图片 URL"""
        if req_format == "wanx":
            return resp_data.get("output", {}).get("image_url")
        elif req_format in ("openai_like", "openai_dalle", "azure_dalle"):
            return resp_data.get("data", [{}])[0].get("url")
        elif req_format == "google_imagen":
            predictions = resp_data.get("predictions", [])
            if predictions:
                return predictions[0].get("bytesBase64Encoded")
            return None
        elif req_format == "sd_api":
            artifacts = resp_data.get("artifacts", [])
            if artifacts:
                return artifacts[0].get("base64")
            return None
        elif req_format == "replicate":
            # Replicate 返回的是 prediction 对象
            if resp_data.get("status") == "succeeded":
                output = resp_data.get("output")
                if isinstance(output, list) and output:
                    return output[0]
                return output
            return None
        elif req_format == "baidu":
            return resp_data.get("data", [{}])[0].get("url")
        elif req_format == "tencent":
            return resp_data.get("data", {}).get("image_url")
        elif req_format == "aws_bedrock":
            artifacts = resp_data.get("artifacts", [])
            if artifacts:
                return artifacts[0].get("base64")
            return None
        return None

    def _probe_model(self, model: Dict) -> bool:
        """
        探测单个模型是否具备生图能力。
        返回 True 表示可用，返回 False 表示不具备或探测失败。
        """
        provider = model.get("provider", "")
        model_id = model.get("id", "")
        base_url = model.get("base_url", "")

        if provider not in IMAGE_GEN_PROVIDER_MAP:
            logger.debug(f"Provider {provider} 不在注册表中，跳过探测")
            return False

        provider_info = IMAGE_GEN_PROVIDER_MAP[provider]
        api_path = provider_info.get("image_api_path", "")
        auth_type = provider_info.get("auth_type", "bearer")
        req_format = provider_info.get("req_format", "openai_like")

        # 获取 API Key
        creds = self._get_credential(model_id)
        if not creds or not creds.get("apiKey"):
            logger.warning(f"模型 {model_id} 缺少 API Key，跳过探测")
            return False

        api_key = creds.get("apiKey", "")

        # 构造请求
        url = f"{base_url}{api_path}"
        headers = {"Content-Type": "application/json"}

        if auth_type == "bearer":
            headers["Authorization"] = f"Bearer {api_key}"
        elif auth_type == "api_key":
            headers["api-key"] = api_key

        payload = self._build_probe_request(provider, req_format)

        try:
            import requests
            logger.info(f"探测生图能力: {provider}/{model_id} -> {url}")
            resp = requests.post(url, json=payload, headers=headers, timeout=60)

            if resp.status_code not in (200, 201):
                logger.warning(f"探测失败 [{provider}/{model_id}]: HTTP {resp.status_code} - {resp.text[:200]}")
                return False

            data = resp.json()
            image_url = self._parse_probe_response(provider, req_format, data)

            if image_url:
                logger.info(f"✓ 探测成功 [{provider}/{model_id}]: 具备生图能力")
                return True
            else:
                logger.warning(f"探测响应无图片 [{provider}/{model_id}]: {str(data)[:200]}")
                return False

        except Exception as e:
            logger.warning(f"探测异常 [{provider}/{model_id}]: {e}")
            return False

    def _get_openclaw_models(self) -> List[Dict]:
        """
        获取已配置且具备生图能力的模型列表。
        流程：缓存 → 初筛 → 探测 → 缓存结果
        """
        # 1. 先尝试从缓存读取
        cached = self._read_cache()
        if cached is not None:
            return cached

        # 2. 初筛候选模型
        candidates = self._prefilter_models()
        if not candidates:
            logger.info("无候选生图模型（初筛为空）")
            self._write_cache([])
            return []

        # 3. 逐个探测生图能力
        valid_models = []
        for model in candidates:
            if self._probe_model(model):
                valid_models.append(model)

        # 4. 写入缓存
        self._write_cache(valid_models)

        logger.info(f"生图模型探测完成: {len(valid_models)}/{len(candidates)} 个可用")
        return valid_models

    def get_ai_model_options(self) -> Dict:
        """
        返回可选的AI生图模型列表。
        从 OpenClaw 配置动态读取并探测已配置的生图模型。
        """
        models = self._get_openclaw_models()

        if models:
            return {
                "need_user_choice": True,
                "choice_type": "ai_model",
                "message": f"已探测到 {len(models)} 个具备生图能力的模型，请选择",
                "options": [{"id": m["id"], "name": f"{m['name']} ({m['provider']})"} for m in models]
            }

        # 没有生图模型时，给出明确提示
        return {
            "need_user_choice": False,
            "choice_type": "ai_model",
            "message": (
                "⚠️ 当前 OpenClaw 未配置任何生图模型，或配置的模型探测失败。\n"
                "请先在 OpenClaw 中配置生图模型（如阿里云通义万图 wanx2.1、MiniMax image-01、"
                "OpenAI dall-e-3 等），或改用「图片接口检索」方式获取图片。\n\n"
                "支持的生图模型 Provider：\n"
                "国内：阿里云（ali-bailian/wanx）、MiniMax、百度、腾讯混元、智谱、商汤、字节\n"
                "国外：OpenAI（DALL-E 3）、Google（Imagen 3）、Stability AI、Replicate、AWS Bedrock、Azure OpenAI"
            ),
            "options": []
        }

    def set_user_choice(self, source: str = None, model_id: str = None):
        """
        保存用户选择到配置文件。

        Args:
            source: 图片来源，"ai" 或 "search"
            model_id: AI模型ID（仅 source="ai" 时需要）
        """
        if source:
            self._config.set_image_source_preference(source)
            self._image_source = source
            if source == "search":
                self._ai_model = None
        if model_id:
            self._config.set_ai_model_preference(model_id)
            self._ai_model = model_id

    def _check_and_prompt_selection(self, img_type: str) -> Dict:
        """
        检查用户是否已做选择，未选择则返回选择提示。
        每次都重新读取配置文件，确保获取最新偏好状态。
        返回 {"proceed": False, "choice_info": {...}} 或 {"proceed": True}
        """
        # 重新读取配置，确保拿到最新偏好
        prefs = self._config.get_image_preferences()
        image_source = prefs.get("image_source")
        ai_model = prefs.get("ai_model")

        if image_source is None:
            return {
                "proceed": False,
                "choice_info": self.get_image_source_options()
            }

        if image_source == "ai" and ai_model is None:
            return {
                "proceed": False,
                "choice_info": self.get_ai_model_options()
            }

        return {"proceed": True}

    # ==================== 生图主方法 ====================

    def generate_cover(self, title: str, keywords: List[str]) -> str:
        """生成封面图"""
        if not title or not isinstance(title, str):
            raise ValueError("title不能为空且必须是字符串")
        if keywords is not None:
            if not isinstance(keywords, list):
                raise ValueError("keywords必须是列表")
            keywords = keywords[:10]

        try:
            logger.info(f"开始生成封面图: {title[:50]}...")
            cover_keywords = self._extract_cover_keywords(title, keywords)

            if self._image_source == "ai":
                img_path = self._generate_by_ai(title, "cover")
                if img_path:
                    logger.info(f"AI生成封面图成功: {img_path}")
                    return img_path
            elif self._image_source == "search":
                images = self._search_all(cover_keywords)
                if images:
                    img_path = self._download_image(images[0], "cover", max_width=900, max_height=500)
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
        if not section or not isinstance(section, str):
            raise ValueError("section不能为空且必须是字符串")
        if keywords is not None:
            if not isinstance(keywords, list):
                raise ValueError("keywords必须是列表")

        try:
            logger.info(f"开始生成插图: {section[:50]}...")
            illust_keywords = self._extract_illustration_keywords(section, keywords)

            if self._image_source == "ai":
                img_path = self._generate_by_ai(section, "illustration")
                if img_path:
                    logger.info(f"AI生成插图成功: {img_path}")
                    return img_path
            elif self._image_source == "search":
                images = self._search_all(illust_keywords)
                if images:
                    img_path = self._download_image(images[0], "illustration", max_width=900, max_height=400)
                    if img_path:
                        logger.info(f"图库下载插图成功: {img_path}")
                        return img_path

            logger.warning(f"未能生成插图: {section[:50]}...")
            return None
        except Exception as e:
            logger.error(f"生成插图失败: {str(e)}", exc_info=True)
            raise

    # ==================== AI 生图 ====================

    def _generate_by_ai(self, prompt: str, img_type: str) -> Optional[str]:
        """根据用户选择的模型调用对应的图像生成 API"""
        if not self._ai_model:
            logger.warning("未选择AI模型，无法生成")
            return None

        full_prompt = self._build_ai_prompt(prompt, img_type)
        size = "1792x1024" if img_type == "cover" else "1024x1024"

        # 读取 OpenClaw credentials 获取 API key
        creds = self._get_credential(self._ai_model)
        if not creds:
            logger.warning(f"未找到模型 {self._ai_model} 的 API 凭证")
            return None

        api_key = creds.get("apiKey", "")
        provider = creds.get("provider", "")
        base_url = creds.get("baseUrl", "")

        # 根据 provider 调用对应的图像生成 API
        if provider == "ali-bailian":
            return self._generate_by_wanx(full_prompt, size, api_key, base_url)
        elif provider == "minimax-cn":
            return self._generate_by_minimax(full_prompt, size, api_key, base_url)
        elif provider == "moonshot":
            return self._generate_by_moonshot_vl(full_prompt, size, api_key, base_url)
        elif provider == "ollama":
            return self._generate_by_ollama(full_prompt, size, api_key, base_url)
        elif provider == "openai":
            return self._generate_by_openai_dalle(full_prompt, size, api_key, base_url)
        elif provider == "google":
            return self._generate_by_google_imagen(full_prompt, size, api_key, base_url)
        elif provider == "stability-ai":
            return self._generate_by_stability(full_prompt, size, api_key, base_url)
        elif provider == "azure-openai":
            return self._generate_by_azure_dalle(full_prompt, size, api_key, base_url)
        elif provider == "aws-bedrock":
            return self._generate_by_aws_bedrock(full_prompt, size, api_key, base_url)
        elif provider == "replicate":
            return self._generate_by_replicate(full_prompt, size, api_key, base_url)
        elif provider == "baidu":
            return self._generate_by_baidu(full_prompt, size, api_key, base_url)
        elif provider == "tencent":
            return self._generate_by_tencent(full_prompt, size, api_key, base_url)
        elif provider == "zhipu":
            return self._generate_by_zhipu(full_prompt, size, api_key, base_url)
        elif provider == "sensetime":
            return self._generate_by_sensetime(full_prompt, size, api_key, base_url)
        elif provider == "bytedance":
            return self._generate_by_bytedance(full_prompt, size, api_key, base_url)
        else:
            logger.warning(f"Provider {provider} 的图像生成 API 暂未实现")
            return None

    def _generate_by_wanx(self, prompt: str, size: str, api_key: str, base_url: str) -> Optional[str]:
        """通义万图（wanx）图像生成 API"""
        try:
            import requests
            url = f"{base_url}/services/aigc/text2image/image-synthesis"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "wanx2.1",
                "input": {"prompt": prompt},
                "parameters": {"size": size, "n": 1}
            }
            logger.info(f"调用 wanx 图像生成 API...")
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            if resp.status_code != 200:
                logger.warning(f"wanx API 返回 {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()
            image_url = data.get("output", {}).get("image_url", "")
            if image_url:
                return self._download_from_url(image_url, "wanx")
            logger.warning(f"wanx 未返回图片 URL: {str(data)[:200]}")
        except Exception as e:
            logger.error(f"wanx 图像生成失败: {e}")
        return None

    def _generate_by_minimax(self, prompt: str, size: str, api_key: str, base_url: str) -> Optional[str]:
        """MiniMax 图像生成 API"""
        try:
            import requests
            # MiniMax 使用 OpenAI 兼容格式
            url = f"{base_url}/images/generations"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            # 解析 size 如 1792x1024 -> 1792x1024
            payload = {
                "model": "image-01",
                "prompt": prompt,
                "size": size,
                "n": 1
            }
            logger.info(f"调用 MiniMax 图像生成 API...")
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            if resp.status_code != 200:
                logger.warning(f"MiniMax API 返回 {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()
            image_url = data.get("data", [{}])[0].get("url", "")
            if image_url:
                return self._download_from_url(image_url, "minimax")
            logger.warning(f"MiniMax 未返回图片 URL: {str(data)[:200]}")
        except Exception as e:
            logger.error(f"MiniMax 图像生成失败: {e}")
        return None

    def _generate_by_moonshot_vl(self, prompt: str, size: str, api_key: str, base_url: str) -> Optional[str]:
        """Moonshot (Kimi) 视觉模型不支持图像生成，返回 None"""
        logger.warning("Moonshot/Kimi 视觉模型暂不支持图像生成，请选择通义万图或 MiniMax")
        return None

    def _generate_by_ollama(self, prompt: str, size: str, api_key: str, base_url: str) -> Optional[str]:
        """Ollama 本地模型（如 llava、sdxs 等多模态模型）"""
        try:
            import requests
            # Ollama 生图通常使用 /api/generate 接口
            # 先尝试标准格式
            url = f"{base_url}/api/generate"
            headers = {"Content-Type": "application/json"}
            # 解析 size
            width, height = map(int, size.split("x"))
            payload = {
                "model": "sdxs",  # 默认使用 sdxs 模型，用户需确保本地已安装
                "prompt": prompt,
                "width": width,
                "height": height,
                "stream": False
            }
            logger.info(f"调用 Ollama 图像生成 API...")
            resp = requests.post(url, json=payload, headers=headers, timeout=180)
            if resp.status_code != 200:
                logger.warning(f"Ollama API 返回 {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()
            image_url = data.get("response", {})
            # Ollama 图像生成可能返回 base64 或 URL
            if isinstance(image_url, dict) and image_url.get("url"):
                return self._download_from_url(image_url["url"], "ollama")
            elif isinstance(image_url, str) and image_url.startswith("data:"):
                # base64 格式，直接保存
                import base64
                img_data = image_url.split(",", 1)
                if len(img_data) == 2:
                    img_bytes = base64.b64decode(img_data[1])
                    filename = f"ollama_{uuid.uuid4().hex[:8]}.png"
                    filepath = self._cache_dir / filename
                    with open(filepath, "wb") as f:
                        f.write(img_bytes)
                    return str(filepath)
            logger.warning(f"Ollama 未返回有效图片: {str(data)[:200]}")
        except Exception as e:
            logger.error(f"Ollama 图像生成失败: {e}")
        return None

    def _generate_by_openai_dalle(self, prompt: str, size: str, api_key: str, base_url: str) -> Optional[str]:
        """OpenAI DALL-E 图像生成 API"""
        try:
            import requests
            # OpenAI 兼容格式
            url = f"{base_url}/v1/images/generations"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024",
                "response_format": "url"
            }
            logger.info(f"调用 OpenAI DALL-E 3 图像生成 API...")
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            if resp.status_code != 200:
                logger.warning(f"OpenAI DALL-E API 返回 {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()
            image_url = data.get("data", [{}])[0].get("url", "")
            if image_url:
                return self._download_from_url(image_url, "openai")
            logger.warning(f"OpenAI DALL-E 未返回图片 URL: {str(data)[:200]}")
        except Exception as e:
            logger.error(f"OpenAI DALL-E 图像生成失败: {e}")
        return None

    def _generate_by_google_imagen(self, prompt: str, size: str, api_key: str, base_url: str) -> Optional[str]:
        """Google Imagen 图像生成 API"""
        try:
            import requests
            # Google Vertex AI Imagen API
            url = f"{base_url}/publishers/google/models/imagen-3/image:predict"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            width, height = map(int, size.split("x"))
            payload = {
                "prompt": prompt,
                "image_size": {"height": height, "width": width},
                "sample_count": 1,
                "aspect_ratio": "16:9" if width > height else "1:1"
            }
            logger.info(f"调用 Google Imagen 3 图像生成 API...")
            resp = requests.post(url, json=payload, headers=headers, timeout=180)
            if resp.status_code != 200:
                logger.warning(f"Google Imagen API 返回 {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()
            predictions = data.get("predictions", [])
            if predictions:
                # Imagen 返回 base64
                bytes_data = predictions[0].get("bytesBase64Encoded", "")
                if bytes_data:
                    import base64
                    img_bytes = base64.b64decode(bytes_data)
                    filename = f"imagen_{uuid.uuid4().hex[:8]}.png"
                    filepath = self._cache_dir / filename
                    with open(filepath, "wb") as f:
                        f.write(img_bytes)
                    logger.info(f"Google Imagen 图片保存成功: {filepath}")
                    return str(filepath)
            logger.warning(f"Google Imagen 未返回图片: {str(data)[:200]}")
        except Exception as e:
            logger.error(f"Google Imagen 图像生成失败: {e}")
        return None

    def _generate_by_stability(self, prompt: str, size: str, api_key: str, base_url: str) -> Optional[str]:
        """Stability AI 图像生成 API"""
        try:
            import requests
            url = f"{base_url}/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            width, height = map(int, size.split("x"))
            payload = {
                "text_prompts": [{"text": prompt, "weight": 1.0}],
                "cfg_scale": 7.5,
                "height": min(height, 1024),
                "width": min(width, 1024),
                "samples": 1,
                "steps": 30
            }
            logger.info(f"调用 Stability AI SDXL 图像生成 API...")
            resp = requests.post(url, json=payload, headers=headers, timeout=180)
            if resp.status_code != 200:
                logger.warning(f"Stability AI API 返回 {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()
            artifacts = data.get("artifacts", [])
            if artifacts:
                import base64
                img_bytes = base64.b64decode(artifacts[0].get("base64", ""))
                filename = f"stability_{uuid.uuid4().hex[:8]}.png"
                filepath = self._cache_dir / filename
                with open(filepath, "wb") as f:
                    f.write(img_bytes)
                logger.info(f"Stability AI 图片保存成功: {filepath}")
                return str(filepath)
            logger.warning(f"Stability AI 未返回图片: {str(data)[:200]}")
        except Exception as e:
            logger.error(f"Stability AI 图像生成失败: {e}")
        return None

    def _generate_by_azure_dalle(self, prompt: str, size: str, api_key: str, base_url: str) -> Optional[str]:
        """Azure OpenAI DALL-E 图像生成 API"""
        try:
            import requests
            # Azure OpenAI 使用部署名称而非 dall-e-3
            url = f"{base_url}/openai/deployments/dall-e-3/images/generations?api-version=2024-02-01"
            headers = {
                "api-key": api_key,
                "Content-Type": "application/json",
            }
            payload = {
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024"
            }
            logger.info(f"调用 Azure OpenAI DALL-E 3 图像生成 API...")
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            if resp.status_code != 200:
                logger.warning(f"Azure DALL-E API 返回 {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()
            image_url = data.get("data", [{}])[0].get("url", "")
            if image_url:
                return self._download_from_url(image_url, "azure")
            logger.warning(f"Azure DALL-E 未返回图片 URL: {str(data)[:200]}")
        except Exception as e:
            logger.error(f"Azure DALL-E 图像生成失败: {e}")
        return None

    def _generate_by_aws_bedrock(self, prompt: str, size: str, api_key: str, base_url: str) -> Optional[str]:
        """AWS Bedrock Stability AI 图像生成 API"""
        try:
            import requests
            # AWS Bedrock 需要 AWS Signature V4 签名
            # API Key 作为 Authorization header（部分网关支持）
            url = f"{base_url}/imagegeneration/stabilityai/stable-diffusion-xl-v1"
            width, height = map(int, size.split("x"))
            payload = {
                "text_prompts": [{"text": prompt, "weight": 1.0}],
                "cfg_scale": 7.5,
                "height": min(height, 1024),
                "width": min(width, 1024),
                "steps": 30,
                "samples": 1
            }
            logger.info(f"调用 AWS Bedrock SDXL 图像生成 API...")
            # AWS Bedrock 需要 AWS 签名，这里使用 Basic Auth（如果配置了）
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=180)
            if resp.status_code != 200:
                logger.warning(f"AWS Bedrock API 返回 {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()
            artifacts = data.get("artifacts", [])
            if artifacts:
                import base64
                img_bytes = base64.b64decode(artifacts[0].get("base64", ""))
                filename = f"bedrock_{uuid.uuid4().hex[:8]}.png"
                filepath = self._cache_dir / filename
                with open(filepath, "wb") as f:
                    f.write(img_bytes)
                logger.info(f"AWS Bedrock 图片保存成功: {filepath}")
                return str(filepath)
            logger.warning(f"AWS Bedrock 未返回图片: {str(data)[:200]}")
        except Exception as e:
            logger.error(f"AWS Bedrock 图像生成失败: {e}")
        return None

    def _generate_by_replicate(self, prompt: str, size: str, api_key: str, base_url: str) -> Optional[str]:
        """Replicate Flux 图像生成 API"""
        try:
            import requests
            # Replicate 使用预测接口
            url = f"{base_url}/v1/predictions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "version": "acl IpShpGBJlsNMENjkEZJDlFNMJAEqSby",
                "input": {
                    "prompt": prompt,
                    "num_outputs": 1,
                    "aspect_ratio": "16:9" if "x" in size and int(size.split("x")[0]) > int(size.split("x")[1]) else "1:1",
                    "output_format": "jpg",
                    "safety_checker": "yes"
                }
            }
            logger.info(f"调用 Replicate Flux 图像生成 API...")
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code not in (200, 201):
                logger.warning(f"Replicate API 返回 {resp.status_code}: {resp.text[:200]}")
                return None
            
            # Replicate 是异步的，需要轮询
            prediction = resp.json()
            prediction_id = prediction.get("id")
            poll_url = f"{base_url}/v1/predictions/{prediction_id}"
            
            import time
            for _ in range(60):  # 最多等 60 * 5 = 300 秒
                time.sleep(5)
                poll_resp = requests.get(poll_url, headers=headers, timeout=30)
                if poll_resp.status_code == 200:
                    result = poll_resp.json()
                    if result.get("status") == "succeeded":
                        output = result.get("output")
                        if isinstance(output, list) and output:
                            image_url = output[0]
                            if image_url.startswith("http"):
                                return self._download_from_url(image_url, "replicate")
                            elif image_url.startswith("data:"):
                                # base64
                                import base64
                                img_data = image_url.split(",", 1)
                                if len(img_data) == 2:
                                    img_bytes = base64.b64decode(img_data[1])
                                    filename = f"replicate_{uuid.uuid4().hex[:8]}.jpg"
                                    filepath = self._cache_dir / filename
                                    with open(filepath, "wb") as f:
                                        f.write(img_bytes)
                                    return str(filepath)
                        break
                    elif result.get("status") == "failed":
                        logger.warning(f"Replicate 生成失败: {result.get('error')}")
                        break
            logger.warning("Replicate 图像生成超时")
        except Exception as e:
            logger.error(f"Replicate 图像生成失败: {e}")
        return None

    def _generate_by_baidu(self, prompt: str, size: str, api_key: str, base_url: str) -> Optional[str]:
        """百度文心一格图像生成 API"""
        try:
            import requests
            url = f"{base_url}/rest/2.0/ernie-vilg/v2/text2image"
            headers = {"Content-Type": "application/json"}
            # 解析 size 如 1792x1024 -> 1024*1024
            width, height = map(int, size.split("x"))
            # 百度只支持特定尺寸
            if width == 1792 and height == 1024:
                size_str = "16:9"
            elif width == height:
                size_str = "1:1"
            else:
                size_str = "1:1"
            payload = {
                "text": prompt,
                "image_size": size_str,
                "style": "adv_flat",
                "num": 1
            }
            logger.info(f"调用百度文心一格图像生成 API...")
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            if resp.status_code != 200:
                logger.warning(f"百度 API 返回 {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()
            if "data" in data and data["data"]:
                image_url = data["data"][0].get("url", "")
                if image_url:
                    return self._download_from_url(image_url, "baidu")
            logger.warning(f"百度文心未返回图片 URL: {str(data)[:200]}")
        except Exception as e:
            logger.error(f"百度文心图像生成失败: {e}")
        return None

    def _generate_by_tencent(self, prompt: str, size: str, api_key: str, base_url: str) -> Optional[str]:
        """腾讯混元图像生成 API"""
        try:
            import requests
            # 腾讯混元使用 HMAC SHA1 认证
            import hmac
            import hashlib
            import time
            url = f"{base_url}/hunyuan/v1/ai_image"
            headers = {"Content-Type": "application/json"}
            width, height = map(int, size.split("x"))
            payload = {
                "prompt": prompt,
                "width": min(width, 1024),
                "height": min(height, 1024),
                "version": "v1.5",
                "samples": 1
            }
            logger.info(f"调用腾讯混元图像生成 API...")
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            if resp.status_code != 200:
                logger.warning(f"腾讯混元 API 返回 {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()
            image_url = data.get("data", {}).get("image_url", "")
            if image_url:
                return self._download_from_url(image_url, "tencent")
            logger.warning(f"腾讯混元未返回图片 URL: {str(data)[:200]}")
        except Exception as e:
            logger.error(f"腾讯混元图像生成失败: {e}")
        return None

    def _generate_by_zhipu(self, prompt: str, size: str, api_key: str, base_url: str) -> Optional[str]:
        """智谱 CogView-4 图像生成 API"""
        try:
            import requests
            url = f"{base_url}/api/paulgraham/t2i"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            width, height = map(int, size.split("x"))
            payload = {
                "prompt": prompt,
                "size": f"{width}x{height}",
                "n": 1
            }
            logger.info(f"调用智谱 CogView-4 图像生成 API...")
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            if resp.status_code != 200:
                logger.warning(f"智谱 API 返回 {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()
            # 智谱可能返回 data[0].url 或直接 url
            image_url = (
                data.get("data", [{}])[0].get("url") or
                data.get("data", {}).get("url") or
                data.get("url", "")
            )
            if image_url:
                return self._download_from_url(image_url, "zhipu")
            logger.warning(f"智谱 CogView 未返回图片 URL: {str(data)[:200]}")
        except Exception as e:
            logger.error(f"智谱 CogView 图像生成失败: {e}")
        return None

    def _generate_by_sensetime(self, prompt: str, size: str, api_key: str, base_url: str) -> Optional[str]:
        """商汤 nova-smooth 图像生成 API"""
        try:
            import requests
            url = f"{base_url}/v1/visionprotect/risenlp/nlpcg/diffusion"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            width, height = map(int, size.split("x"))
            payload = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "num_images": 1
            }
            logger.info(f"调用商汤 nova-smooth 图像生成 API...")
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            if resp.status_code != 200:
                logger.warning(f"商汤 API 返回 {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()
            image_url = data.get("data", {}).get("image_url", "")
            if not image_url:
                image_url = data.get("image_url", "")
            if image_url:
                return self._download_from_url(image_url, "sensetime")
            logger.warning(f"商汤未返回图片 URL: {str(data)[:200]}")
        except Exception as e:
            logger.error(f"商汤图像生成失败: {e}")
        return None

    def _generate_by_bytedance(self, prompt: str, size: str, api_key: str, base_url: str) -> Optional[str]:
        """字节豆包 SDXL 图像生成 API"""
        try:
            import requests
            url = f"{base_url}/cv/sdxl/txt2img"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            width, height = map(int, size.split("x"))
            payload = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "num_images": 1,
                "style_id": 0
            }
            logger.info(f"调用字节豆包 SDXL 图像生成 API...")
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            if resp.status_code != 200:
                logger.warning(f"字节豆包 API 返回 {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()
            image_url = data.get("data", {}).get("image_url", "")
            if not image_url:
                image_url = data.get("image_url", "")
            if image_url:
                return self._download_from_url(image_url, "bytedance")
            logger.warning(f"字节豆包未返回图片 URL: {str(data)[:200]}")
        except Exception as e:
            logger.error(f"字节豆包图像生成失败: {e}")
        return None

    def _build_ai_prompt(self, prompt: str, img_type: str) -> str:
        """构建 AI 生成的 prompt"""
        style_guide = (
            "微信公众号文章配图，简约现代风格，"
            "清新配色，专业商务感，适合文章内容可视化。"
        )
        if img_type == "cover":
            return f"{prompt}，{style_guide}，横版图片 16:9 比例，高清摄影风格"
        else:
            return f"{prompt}，{style_guide}，方形图片 1:1 比例，插画风格"

    def _compress_image(self, filepath: str, max_width: int = 900, max_height: int = 900, quality: int = 85) -> bool:
        """使用 Pillow 压缩并缩放图片，返回是否成功"""
        try:
            from PIL import Image
            with Image.open(filepath) as img:
                # 转换模式（RGBA/P/LA/PA → RGB，避免 JPEG 不支持）
                if img.mode in ("RGBA", "P", "LA", "PA"):
                    rgb_img = img.convert("RGB")
                else:
                    rgb_img = img
                # 缩放，保证不超过 max_width × max_height
                rgb_img.thumbnail((max_width, max_height), Image.LANCZOS)
                rgb_img.save(filepath, "JPEG", quality=quality, optimize=True)
            return True
        except ImportError:
            logger.warning("Pillow 未安装，图片未压缩")
            return False
        except Exception as e:
            logger.warning(f"图片压缩失败，使用原图: {e}")
            return False

    def _download_from_url(self, url: str, prefix: str = "ai",
                          max_width: int = 900, max_height: int = 900) -> Optional[str]:
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
                # 压缩图片
                self._compress_image(str(filepath), max_width=max_width, max_height=max_height)
                return str(filepath)
            else:
                logger.warning(f"AI 图片下载失败 HTTP {resp.status_code}")
        except Exception as e:
            logger.error(f"下载 AI 图片失败: {str(e)}")
        return None

    # ==================== 图库检索 ====================

    def _search_all(self, keywords: str, count: int = 5) -> List[Dict]:
        """双 API 搜索，自动切换"""
        if not keywords or not isinstance(keywords, str):
            return []
        if not isinstance(count, int) or count < 1 or count > 30:
            count = 5

        try:
            if self._pexels_api_key:
                images = self._search_pexels(keywords, count)
                if images:
                    return images
            if self._unsplash_api_key:
                images = self._search_unsplash(keywords, count)
                if images:
                    return images
            logger.warning(f"所有图库搜索均未返回结果: {keywords}")
            return []
        except Exception as e:
            logger.error(f"图片搜索失败: {str(e)}", exc_info=True)
            return []

    def _search_pexels(self, keywords: str, count: int = 5) -> List[Dict]:
        if not self._pexels_api_key:
            return []
        try:
            import requests
            url = f"https://api.pexels.com/v1/search?query={keywords}&per_page={count}&orientation=landscape"
            headers = {"Authorization": self._pexels_api_key}
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return []
            data = resp.json()
            photos = data.get("photos", [])
            return [
                {
                    # "large" 约 1050px，"medium" 约 350px，用 large 兼顾质量与大小
                    "url": p.get("src", {}).get("large"),
                    "thumb_url": p.get("src", {}).get("medium"),
                    "author": p.get("photographer", "Unknown"),
                    "source": "Pexels"
                }
                for p in photos
            ]
        except Exception as e:
            logger.error(f"Pexels搜索失败: {str(e)}")
            return []

    def _search_unsplash(self, keywords: str, count: int = 5) -> List[Dict]:
        if not self._unsplash_api_key:
            return []
        try:
            import requests
            url = f"https://api.unsplash.com/search/photos?query={keywords}&per_page={count}&orientation=landscape"
            headers = {"Authorization": f"Client-ID {self._unsplash_api_key}"}
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
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
        except Exception as e:
            logger.error(f"Unsplash搜索失败: {str(e)}")
            return []

    def _download_image(self, image_info: Dict, prefix: str,
                       max_width: int = 900, max_height: int = 600) -> Optional[str]:
        """下载图片（带压缩）"""
        url = image_info.get("url", "")
        if not url:
            return None

        allowed_domains = ["images.pexels.com", "unsplash.com", "plus.unsplash.com"]
        if not any(domain in url for domain in allowed_domains):
            return None

        try:
            import requests
            filename = f"{prefix}_{uuid.uuid4().hex[:8]}.jpg"
            filepath = self._cache_dir / filename
            if ".." in str(filepath) or str(filepath).startswith("/"):
                filepath = filepath.resolve()
                if not str(filepath).startswith(str(self._cache_dir.resolve())):
                    return None
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                logger.info(f"图片下载成功: {filepath}")
                # 压缩图片
                self._compress_image(str(filepath), max_width=max_width, max_height=max_height)
                return str(filepath)
        except Exception as e:
            logger.error(f"图片下载失败: {str(e)}")
        return None

    # ==================== 工具方法 ====================

    def _extract_cover_keywords(self, title: str, keywords: List[str]) -> str:
        if not title:
            return ""
        return " ".join(title.split()[:3] + (keywords[:3] if keywords else []))

    def _extract_illustration_keywords(self, section: str, keywords: List[str]) -> str:
        if not section:
            return ""
        return " ".join(section.split()[:3])

    def generate_and_upload(self, title_or_section: str, keywords: List[str],
                          material_skill, img_type: str = "illustration") -> Dict:
        """生成图片并上传到微信素材库"""
        result = {"local_path": None, "wechat_url": None, "media_id": None}

        try:
            if img_type == "cover":
                local_path = self.generate_cover(title_or_section, keywords)
            else:
                local_path = self.generate_illustration(title_or_section, keywords)

            if not local_path or not os.path.exists(local_path):
                logger.warning(f"[{img_type}] 图片生成失败: {title_or_section[:30]}")
                return result

            result["local_path"] = local_path

            upload_result = material_skill.upload_image(local_path)
            if upload_result:
                result["wechat_url"] = upload_result.get("url", "")
                result["media_id"] = upload_result.get("media_id", "")
                logger.info(f"[{img_type}] 生成并上传成功: {result['wechat_url'][:50] if result['wechat_url'] else 'failed'}...")
            return result
        except Exception as e:
            logger.error(f"[{img_type}] 生成上传失败: {e}")
            return result

    def search_image(self, query: str, count: int = 5) -> List[Dict]:
        """搜索图库图片并下载到本地

        Args:
            query: 搜索关键词
            count: 请求图片数量，默认5张

        Returns:
            图片信息列表，每个元素含 url（原始链接）和 local_path（本地文件路径）
        """
        if not query or not isinstance(query, str):
            return []
        if not isinstance(count, int) or count < 1:
            count = 5

        results = []
        images = self._search_all(query, count)
        for img in images:
            local_path = self._download_image(img, "search")
            if local_path:
                results.append({
                    "url": img.get("url", ""),
                    "local_path": local_path
                })
            if len(results) >= count:
                break
        return results

    def generate_image(self, prompt: str, size: str = "1024x1024") -> Dict:
        """AI 生成图片

        Args:
            prompt: 图片描述提示词
            size: 图片尺寸，默认 1024x1024（可以是 1792x1024 用于封面）

        Returns:
            {"local_path": "本地文件路径"}
        """
        if not prompt or not isinstance(prompt, str):
            return {"local_path": None}

        img_type = "cover" if "x" in size and int(size.split("x")[0]) > 1024 else "illustration"
        local_path = self._generate_by_ai(prompt, img_type)
        return {"local_path": local_path}

    def batch_generate(self, title: str, sections: List[str], keywords: List[str]) -> Dict:
        """批量生成图片"""
        if not title or not isinstance(title, str):
            raise ValueError("title不能为空且必须是字符串")
        if not sections or not isinstance(sections, list):
            raise ValueError("sections不能为空且必须是列表")
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
