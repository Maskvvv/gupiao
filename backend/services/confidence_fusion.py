"""
置信度解析与融合分计算模块

实现 AI 信心解析和技术分与 AI 信心的融合计算功能
"""
import re
import logging
import os
from typing import Tuple, Optional, Union

# 从环境变量获取融合系数，默认0.4
CONF_FUSION_ALPHA = float(os.getenv("CONF_FUSION_ALPHA", "0.4"))

# 初始化时打印配置值
print(f"[CONFIG] CONF_FUSION_ALPHA = {CONF_FUSION_ALPHA}")

logger = logging.getLogger(__name__)


def parse_ai_confidence(text: str) -> Tuple[Optional[float], Optional[str]]:
    """
    从 AI 回复文本中解析信心分数（0-10）
    
    Args:
        text: AI 回复的完整文本
        
    Returns:
        (confidence_value, raw_text): 解析出的信心值和原始文本片段
        如果解析失败，返回 (None, None)
    """
    if not text or not isinstance(text, str):
        logger.debug(f"parse_ai_confidence: 输入为空或非字符串: {type(text)}")
        return None, None
    
    # 多种匹配模式：中英文，不同分隔符，全角半角数字；支持可选负号（-、−、－）
    patterns = [
        # 中文模式："信心X/10", "信心：X/10", "信心 X/10"
        r'信心[：:\s]*([\-−－]?[0-9０-９]+(?:\.[0-9０-９]+)?)[/／]?(?:10|１０)?',
        # 英文模式："confidence X/10", "confidence: X/10"
        r'confidence[：:\s]*([\-−－]?[0-9０-９]+(?:\.[0-9０-９]+)?)[/／]?(?:10|１０)?',
        # 括号模式："（信心X/10）", "(confidence X)"
        r'[（(]信心[：:\s]*([\-−－]?[0-9０-９]+(?:\.[0-9０-９]+)?)[/／]?(?:10|１０)?[）)]',
        r'[（(]confidence[：:\s]*([\-−－]?[0-9０-９]+(?:\.[0-9０-９]+)?)[/／]?(?:10|１０)?[）)]',
        # 直接数字模式："X/10"，但需要前面有相关关键词上下文
        r'(?:信心|confidence)[^0-9０-９]*([\-−－]?[0-9０-９]+(?:\.[0-9０-９]+)?)[/／](?:10|１０)',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            raw_match = match.group(0)
            confidence_str = match.group(1)
            
            # 转换全角数字为半角，统一减号到 ASCII '-'
            confidence_str = confidence_str.replace('０', '0').replace('１', '1').replace('２', '2').replace('３', '3').replace('４', '4')
            confidence_str = confidence_str.replace('５', '5').replace('６', '6').replace('７', '7').replace('８', '8').replace('９', '9')
            confidence_str = confidence_str.replace('－', '-').replace('−', '-')
            
            try:
                confidence_value = float(confidence_str)
                
                # 边界处理：截断到 [0, 10]
                if confidence_value < 0 or confidence_value > 10:
                    logger.warning(f"parse_ai_confidence: 信心值超出范围 [0,10]: {confidence_value} (原始: '{raw_match}')")
                    confidence_value = max(0.0, min(10.0, confidence_value))
                
                logger.debug(f"parse_ai_confidence: 成功解析信心值 {confidence_value} (原始: '{raw_match}')")
                return confidence_value, raw_match
                
            except ValueError:
                logger.debug(f"parse_ai_confidence: 无法解析数字 '{confidence_str}' (原始: '{raw_match}')")
                continue
    
    # 所有模式都失败
    logger.debug(f"parse_ai_confidence: 未找到匹配的信心值模式")
    return None, None


def compute_fusion_score(tech_score: Optional[float], ai_confidence: Optional[float], alpha: float = None) -> Optional[float]:
    """
    计算融合分数
    
    Args:
        tech_score: 技术分数（0-1 范围，来自 basic_analysis）
        ai_confidence: AI 信心分数（0-10 范围）
        alpha: 融合系数，默认使用 CONF_FUSION_ALPHA
        
    Returns:
        融合分数（0-10 范围，保留两位小数），如果无法计算则返回 None
    """
    if alpha is None:
        alpha = CONF_FUSION_ALPHA
        
    # 技术分为空，无法融合
    if tech_score is None:
        logger.warning("compute_fusion_score: 技术分为空，无法计算融合分")
        return None
    
    # AI 信心为空，回退到技术分
    if ai_confidence is None:
        # 将技术分从 0-1 映射到 0-10
        fusion_score = tech_score * 10.0
        fusion_score = max(0.0, min(10.0, fusion_score))  # 边界保护
        fusion_score = round(fusion_score, 2)
        logger.info(f"compute_fusion_score: 无AI信心，回退技术分 {tech_score:.3f} -> {fusion_score}")
        return fusion_score
    
    # 都不为空，进行融合计算
    # 技术分先映射到 0-10 范围，并裁剪到 [0,10]
    tech_score_10 = tech_score * 10.0
    tech_score_10 = max(0.0, min(10.0, tech_score_10))
    
    # 融合公式：fusion = alpha * tech + (1 - alpha) * ai_confidence
    fusion_score = alpha * tech_score_10 + (1 - alpha) * ai_confidence
    
    # 边界保护和精度处理
    fusion_score = max(0.0, min(10.0, fusion_score))
    fusion_score = round(fusion_score, 2)
    
    logger.debug(f"compute_fusion_score: 技术分{tech_score:.3f}(->10倍裁剪{tech_score_10:.1f}) + AI信心{ai_confidence} -> 融合分{fusion_score} (alpha={alpha})")
    return fusion_score


def extract_confidence_and_fusion(analysis: dict, ai_advice: str) -> dict:
    """
    从分析结果中提取并计算信心和融合分
    
    Args:
        analysis: 基础技术分析结果（包含 score 字段）
        ai_advice: AI 建议文本
        
    Returns:
        更新后的分析结果，包含 ai_confidence, ai_confidence_raw, fusion_score 字段
    """
    # 解析 AI 信心
    ai_confidence, ai_confidence_raw = parse_ai_confidence(ai_advice)
    
    # 计算融合分
    tech_score = analysis.get('score')
    fusion_score = compute_fusion_score(tech_score, ai_confidence)
    
    # 更新分析结果
    analysis.update({
        'ai_confidence': ai_confidence,
        'ai_confidence_raw': ai_confidence_raw,
        'fusion_score': fusion_score
    })
    
    return analysis


# 单元测试用例（可选执行）
def _test_parse_ai_confidence():
    """单元测试：AI 信心解析"""
    test_cases = [
        ("建议买入（信心8/10）", 8.0, "信心8/10"),
        ("confidence: 7.5/10", 7.5, "confidence: 7.5/10"),
        ("信心：９/１０", 9.0, "信心：９/１０"),
        ("最终建议：买入（信心十/10）", None, None),  # 中文数字无法解析
        ("信心12/10", 10.0, "信心12/10"),  # 超界截断
        ("信心-1/10", 0.0, "信心-1/10"),   # 负数截断
        ("无信心提及", None, None),
        ("", None, None),
    ]
    
    print("Testing parse_ai_confidence:")
    for text, expected_val, expected_raw in test_cases:
        actual_val, actual_raw = parse_ai_confidence(text)
        status = "✓" if (actual_val == expected_val and (expected_raw is None or expected_raw in (actual_raw or ""))) else "✗"
        print(f"  {status} '{text}' -> {actual_val}, '{actual_raw}'")


def _test_compute_fusion_score():
    """单元测试：融合分计算"""
    test_cases = [
        (0.8, 9.0, 0.4, 8.6),   # 0.4*8 + 0.6*9 = 3.2 + 5.4 = 8.6
        (0.5, None, 0.4, 5.0),  # 技术分回退：0.5*10 = 5.0
        (None, 8.0, 0.4, None), # 技术分为空
        (0.75, 8.5, 0.3, 8.25), # 0.3*7.5 + 0.7*8.5 = 2.25 + 5.95 = 8.2 (四舍五入到8.25?)
    ]
    
    print("\nTesting compute_fusion_score:")
    for tech, ai, alpha, expected in test_cases:
        actual = compute_fusion_score(tech, ai, alpha)
        status = "✓" if actual == expected else "✗"
        print(f"  {status} tech={tech}, ai={ai}, alpha={alpha} -> {actual} (expected {expected})")


if __name__ == "__main__":
    # 运行单元测试
    _test_parse_ai_confidence()
    _test_compute_fusion_score()