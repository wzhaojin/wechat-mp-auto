"""
微信公众号自动化 - 图片处理 Skill
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from .base_skill import BaseSkill

logger = logging.getLogger(__name__)


class ImageProcessorSkill(BaseSkill):
    """图片处理 - 微信格式"""
    
    COVER_SIZE = (900, 500)
    COVER_MAX_SIZE = 2 * 1024 * 1024
    ILLUST_MIN_WIDTH = 640
    ILLUST_MAX_WIDTH = 1080
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache_dir = Path.home() / ".cache" / "wechat-mp-auto" / "processed"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
    
    def process_cover_image(self, image_path: str) -> Dict:
        """处理封面图"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片不存在: {image_path}")
        
        # 1. 调整尺寸
        resized = self._resize_image(image_path, self.COVER_SIZE[0], self.COVER_SIZE[1])
        # 2. 压缩
        compressed = self._compress_image(resized, self.COVER_MAX_SIZE)
        # 3. 去水印
        cleaned = self.remove_watermark(compressed)
        # 4. 转换格式
        final = self._convert_format(cleaned, "jpg")
        
        return {"path": final, "width": self.COVER_SIZE[0], "height": self.COVER_SIZE[1], "size": os.path.getsize(final)}
    
    def process_illustration(self, image_path: str) -> Dict:
        """处理插图"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片不存在: {image_path}")
        
        original_size = self._get_image_size(image_path)
        width = original_size[0]
        
        new_width = width
        if width > self.ILLUST_MAX_WIDTH:
            new_width = self.ILLUST_MAX_WIDTH
        elif width < self.ILLUST_MIN_WIDTH:
            new_width = self.ILLUST_MIN_WIDTH
        
        resized = self._resize_image(image_path, new_width, None)
        compressed = self._compress_image(resized, 5 * 1024 * 1024)
        cleaned = self.remove_watermark(compressed)
        final = self._convert_format(cleaned, "jpg")
        
        new_size = self._get_image_size(final)
        return {"path": final, "width": new_size[0], "height": new_size[1], "size": os.path.getsize(final)}
    
    def remove_watermark(self, image_path: str) -> str:
        """
        去除水印 - 支持多种方法
        方法1: 边缘裁剪（适用于角落水印）
        方法2: 简单模糊（适用于淡色水印）
        """
        if not os.path.exists(image_path):
            logger.warning(f"图片不存在，跳过去水印: {image_path}")
            return image_path
        
        try:
            from PIL import Image, ImageFilter
            import uuid
            
            img = Image.open(image_path)
            width, height = img.size
            
            # 检测是否为透明背景的 PNG（通常自带水印）
            if img.format == 'PNG' and img.mode == 'RGBA':
                # 尝试简单去水印：检测并移除半透明区域
                img = self._remove_transparent_watermark(img)
            
            # 检测角落是否有水印（通过分析边缘像素）
            # 如果图片有明显的角落文字/LOGO，尝试裁剪
            corner_watermark = self._detect_corner_watermark(img)
            if corner_watermark:
                img = self._crop_corner_watermark(img, corner_watermark)
                logger.info(f"已裁剪角落水印: {corner_watermark}")
            
            # 如果以上都未处理，尝试边缘裁剪（微信水印通常在角落）
            # 默认裁剪右下角 5% 区域
            if width > 400 and height > 200:
                crop_ratio = 0.05
                cropped = img.crop((
                    0, 0,
                    int(width * (1 - crop_ratio)),
                    int(height * (1 - crop_ratio))
                ))
                
                # 检查裁剪后是否合理
                new_w, new_h = cropped.size
                if new_w > width * 0.7 and new_h > height * 0.7:
                    # 保存处理后的图片
                    output_path = image_path.replace(".jpg", f"_cleaned_{uuid.uuid4().hex[:4]}.jpg")
                    cropped.convert('RGB').save(output_path, 'JPEG', quality=90)
                    logger.info(f"去水印处理完成: {output_path}")
                    return output_path
            
            # 无需处理
            return image_path
            
        except ImportError:
            logger.warning("PIL 未安装，跳过去水印处理")
            return image_path
        except Exception as e:
            logger.warning(f"去水印处理失败: {str(e)}，返回原图")
            return image_path
    
    def _detect_corner_watermark(self, img) -> Optional[str]:
        """检测角落是否有水印"""
        try:
            width, height = img.size
            pixels = img.load()
            
            # 检查右下角是否有水印（通常为半透明文字/LOGO）
            # 采样右下角 10% 区域
            corner_region = []
            for x in range(int(width * 0.9), width):
                for y in range(int(height * 0.9), height):
                    if img.mode == 'RGBA':
                        alpha = pixels[x, y][3]
                        if alpha > 0 and alpha < 255:  # 半透明
                            return "bottom_right"
                    elif img.mode == 'RGB':
                        # 检查非白色像素占比
                        r, g, b = pixels[x, y]
                        if r < 250 or g < 250 or b < 250:  # 非纯白
                            return "bottom_right"
            
            return None
        except Exception:
            return None
    
    def _crop_corner_watermark(self, img, position: str):
        """裁剪角落水印"""
        width, height = img.size
        crop_ratio = 0.08  # 裁剪 8%
        
        if position == "bottom_right":
            return img.crop((
                0, 0,
                int(width * (1 - crop_ratio)),
                int(height * (1 - crop_ratio))
            ))
        elif position == "bottom_left":
            return img.crop((
                int(width * crop_ratio), 0,
                width,
                int(height * (1 - crop_ratio))
            ))
        elif position == "top_right":
            return img.crop((
                0, int(height * crop_ratio),
                int(width * (1 - crop_ratio)),
                height
            ))
        
        return img
    
    def _remove_transparent_watermark(self, img) :
        """移除 PNG 中的半透明水印"""
        width, height = img.size
        pixels = img.load()
        
        # 找出半透明区域
        transparent_pixels = []
        for x in range(width):
            for y in range(height):
                if pixels[x, y][3] < 200:  # 半透明
                    transparent_pixels.append((x, y))
        
        # 如果半透明区域超过一定比例，认为是水印
        if len(transparent_pixels) > width * height * 0.05:
            # 将半透明区域设为完全透明
            for x, y in transparent_pixels:
                pixels[x, y] = (255, 255, 255, 0)
        
        return img
    
    def _resize_image(self, image_path: str, width: int, height: Optional[int] = None) -> str:
        """调整图片尺寸"""
        try:
            from PIL import Image
            
            img = Image.open(image_path)
            
            # 保持比例
            if height is None:
                # 只指定宽度
                ratio = width / img.size[0]
                height = int(img.size[1] * ratio)
            
            resized = img.resize((width, height), Image.Resampling.LANCZOS)
            
            output = image_path.replace(".jpg", f"_resized_{width}x{height}.jpg")
            # 避免覆盖原图
            if output == image_path:
                output = image_path.rsplit(".", 1)[0] + f"_resized.jpg"
            
            resized.save(output, 'JPEG', quality=90)
            return output
        except ImportError:
            # 降级使用 sips
            output = image_path.replace(".jpg", f"_resized.jpg")
            cmd = ["sips", "-z", str(height), str(width), image_path, "--out", output]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                return output
            except Exception:
                return image_path
        except Exception as e:
            logger.warning(f"图片缩放失败: {str(e)}")
            return image_path
    
    def _compress_image(self, image_path: str, max_size: int) -> str:
        """压缩图片"""
        try:
            from PIL import Image
            
            img = Image.open(image_path)
            current_size = os.path.getsize(image_path)
            
            if current_size <= max_size:
                return image_path
            
            # 逐步压缩
            quality = 90
            while quality > 30:
                output = image_path.replace(".jpg", f"_compressed_q{quality}.jpg")
                img.save(output, 'JPEG', quality=quality, optimize=True)
                
                if os.path.getsize(output) <= max_size:
                    return output
                
                quality -= 10
            
            # 最低质量
            return output
        except ImportError:
            return image_path
        except Exception as e:
            logger.warning(f"图片压缩失败: {str(e)}")
            return image_path
    
    def _convert_format(self, image_path: str, format: str) -> str:
        """转换图片格式"""
        output = image_path.rsplit(".", 1)[0] + f".{format}"
        
        # 如果格式没变，直接返回
        if output == image_path:
            return image_path
        
        try:
            from PIL import Image
            img = Image.open(image_path)
            
            if format.lower() in ['jpg', 'jpeg']:
                # 转 RGB（去除 alpha 通道）
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    if img.mode in ('RGBA', 'LA'):
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                img = img.convert('RGB')
            
            img.save(output, format.upper() if format.upper() != 'JPG' else 'JPEG')
            return output
        except ImportError:
            # 降级使用 sips
            cmd = ["sips", "-s", f"format {format}", image_path, "--out", output]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                return output
            except Exception:
                return image_path
        except Exception as e:
            logger.warning(f"图片格式转换失败: {str(e)}")
            return image_path
    
    def _get_image_size(self, image_path: str) -> Tuple[int, int]:
        """获取图片尺寸"""
        try:
            from PIL import Image
            with Image.open(image_path) as img:
                return img.size
        except Exception:
            return (800, 600)
