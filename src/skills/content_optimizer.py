"""
微信公众号自动化 - 内容优化技能
去除AI生成内容的痕迹，使文本更自然、更有文人气息

从 wechat-allauto-gzh 项目借鉴并适配
"""

import re
import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class HumanizeConfig:
    """人性化配置选项"""
    # 替换强度 (0.0-1.0)
    intensity: float = 0.7
    
    # 是否启用口语化表达
    enable_colloquial: bool = True
    
    # 是否启用情感词增强
    enable_emotion: bool = True
    
    # 是否添加个人化视角
    enable_personal: bool = True
    
    # 是否打乱完美句式（添加小瑕疵）
    add_imperfections: bool = True
    
    # 风格倾向: "warm"(温暖), "professional"(专业), "casual"(随意)
    style_tone: str = "warm"


class ContentOptimizer:
    """内容优化器：去除AI痕迹，添加人文气息"""
    
    # AI常见词汇/句式 → 人性化替换
    AI_PATTERNS: List[Tuple[str, List[str]]] = [
        # 正式书面语 → 口语化表达
        (r"首先，", ["一开始，", "最开始，", "说起来，"]),
        (r"其次，", ["接着，", "然后呢，", "再往后，"]),
        (r"最后，", ["到最后，", "终于，", "快结束时，"]),
        (r"综上所述", ["总的来说", "说白了", "简单讲"]),
        (r"由此可见", ["这么看来", "你能发现", "其实"]),
        (r"值得注意的是", ["有意思的是", "你发现没", "挺神奇的是"]),
        (r"毫无疑问", ["说实话", "说真的", "坦白讲"]),
        (r"很大程度上", ["差不多", "基本", "大多数时候"]),
        
        # 机械连接词 → 自然过渡
        (r"此外，", ["另外，", "还有，", "对了，"]),
        (r"然而，", ["但是，", "不过，", "可问题是，"]),
        (r"因此，", ["所以，", "这就导致", "结果就是"]),
        (r"尽管如此", ["虽然这样", "就算这样", "哪怕如此"]),
        
        # AI套话 → 真实表达
        (r"让我们.*?看看", ["来看看", "瞧瞧", "感受下"]),
        (r"我们需要理解", ["你得明白", "说实话", "坦白说"]),
        (r"这意味着", ["这说明", "也就是说", "等同于"]),
        (r"你会发现", ["你能看到", "想象一下"]),
        
        # 过于正式的词汇
        (r"非常", ["挺", "蛮", "特别", "超级"]),
        (r"十分", ["蛮", "挺", "相当"]),
        (r"极其", ["特别", "超级", "巨"]),
        (r"相当", ["挺", "蛮", "蛮"]),
        (r"因此", ["所以", "于是"]),
    ]
    
    # 情感增强词
    EMOTION_WORDS: Dict[str, List[str]] = {
        "positive": ["真心", "确实", "说实在的", "不得不說", "坦白說"],
        "thinking": ["琢磨一下", "细想一下", "想想看", "寻思一下"],
        "surprise": ["意想不到", "出乎意料", "没想到", "竟然"],
        "emphasis": ["确实", "说实话", "真的", "确实是这样"],
    }
    
    def __init__(self, config: Optional[HumanizeConfig] = None):
        self.config = config or HumanizeConfig()
    
    def optimize(self, text: str) -> str:
        """
        优化文本，去除AI痕迹
        
        Args:
            text: 原始文本
            
        Returns:
            优化后的文本
        """
        result = text
        
        # 1. 替换AI模式
        if self.config.intensity > 0:
            result = self._replace_ai_patterns(result)
        
        # 2. 添加情感词
        if self.config.enable_emotion and self.config.intensity > 0.3:
            result = self._add_emotion_words(result)
        
        # 3. 个性化视角
        if self.config.enable_personal and self.config.intensity > 0.5:
            result = self._add_personal_perspective(result)
        
        # 4. 添加小瑕疵（打破完美）
        if self.config.add_imperfections and self.config.intensity > 0.6:
            result = self._add_imperfections(result)
        
        # 5. 清理多余空格
        result = self._cleanup_whitespace(result)
        
        return result
    
    def _replace_ai_patterns(self, text: str) -> str:
        """替换AI常见模式"""
        result = text
        
        for pattern, replacements in self.AI_PATTERNS:
            def replacer(match):
                if random.random() < self.config.intensity:
                    return random.choice(replacements)
                return match.group(0)
            
            result = re.sub(pattern, replacer, result, flags=re.IGNORECASE)
        
        return result
    
    def _add_emotion_words(self, text: str) -> str:
        """添加情感增强词，保护 Markdown 格式"""
        # Step 1: 保护 Markdown 标题行（# 开头或 ## 开头的行）
        protected_lines = []
        
        def protect_line(m):
            protected_lines.append(m.group(0))
            return f'\x00PROTECTED_LINE_{len(protected_lines)-1}\x00'
        
        text = re.sub(r'^#{1,6} .+$', protect_line, text, flags=re.MULTILINE)
        
        # Step 2: 分割句子并添加情感词
        sentences = re.split(r'([。！？.!?])', text)
        result = []
        
        for i, sentence in enumerate(sentences):
            if sentence in '。！？.!?':
                result.append(sentence)
                continue
            
            # 随机添加情感词（仅在非保护行）
            if random.random() < 0.15 * self.config.intensity and sentence.strip():
                # 跳过标题行和 Markdown 特殊行
                if not sentence.startswith('\x00PROTECTED_LINE'):
                    emotion_type = random.choice(list(self.EMOTION_WORDS.keys()))
                    emotion_word = random.choice(self.EMOTION_WORDS[emotion_type])
                    sentence = emotion_word + "，" + sentence.lstrip()
            
            result.append(sentence)
        
        text = ''.join(result)
        
        # Step 3: 恢复保护行
        for i, line in enumerate(protected_lines):
            text = text.replace(f'\x00PROTECTED_LINE_{i}\x00', line)
        
        return text
    
    def _add_personal_perspective(self, text: str) -> str:
        """添加个人化视角，保护 Markdown 格式"""
        personal_phrases = [
            "我觉得", "我个人认为", "以我的经验",
            "从我的角度来看", "说实话", "不得不说"
        ]
        
        # Step 1: 保护 Markdown 标题行
        protected_lines = []
        
        def protect_line(m):
            protected_lines.append(m.group(0))
            return f'\x00PROTECTED_LINE_{len(protected_lines)-1}\x00'
        
        text = re.sub(r'^#{1,6} .+$', protect_line, text, flags=re.MULTILINE)
        
        # Step 2: 分割句子并添加个人视角
        sentences = re.split(r'([。！？.!?])', text)
        result = []
        
        for i, sentence in enumerate(sentences):
            if sentence in '。！？.!?':
                result.append(sentence)
                continue
            
            # 在某些句子开头添加个人视角（跳过保护行）
            if random.random() < 0.08 * self.config.intensity and len(sentence) > 10:
                if not sentence.startswith('\x00PROTECTED_LINE'):
                    phrase = random.choice(personal_phrases)
                    sentence = phrase + "，" + sentence.lstrip()
            
            result.append(sentence)
        
        text = ''.join(result)
        
        # Step 3: 恢复保护行
        for i, line in enumerate(protected_lines):
            text = text.replace(f'\x00PROTECTED_LINE_{i}\x00', line)
        
        return text
    
    def _add_imperfections(self, text: str) -> str:
        """添加小瑕疵，打破完美句式"""
        imperfections = [
            (r"，", ["——", "…", "，那个，"]),
            (r"。", ["。嗯，", "。对了，"])
        ]
        
        result = text
        for pattern, replacements in imperfections:
            matches = list(re.finditer(pattern, result))
            if len(matches) > 3:
                to_replace = random.sample(matches, min(len(matches) // 10 + 1, 3))
                for match in sorted(to_replace, key=lambda m: m.start(), reverse=True):
                    replacement = random.choice(replacements)
                    result = result[:match.start()] + replacement + result[match.end():]
        
        return result
    
    def _cleanup_whitespace(self, text: str) -> str:
        """清理多余的空白字符"""
        result = re.sub(r' +', ' ', text)
        result = re.sub(r'　+', '　', result)
        result = '\n'.join(line.strip() for line in result.split('\n'))
        return result.strip()


# 便捷函数
def humanize_text(text: str, intensity: float = 0.7) -> str:
    """
    快速优化文本，去除AI痕迹
    
    Args:
        text: 原始文本
        intensity: 优化强度 (0.0-1.0)
        
    Returns:
        优化后的文本
        
    Example:
        >>> text = "首先，我们需要理解这个概念。其次，我们要分析其应用场景。"
        >>> humanize_text(text)
        "一开始，你得明白这个概念。接着呢，咱们看看它能在哪儿用。"
    """
    config = HumanizeConfig(intensity=intensity)
    optimizer = ContentOptimizer(config)
    return optimizer.optimize(text)
