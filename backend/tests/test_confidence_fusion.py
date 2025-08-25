# -*- coding: utf-8 -*-
"""
Unit tests for services.confidence_fusion
- parse_ai_confidence: regex variants, full/half width, decimals, out-of-range, negatives, invalid strings
- compute_fusion_score: fallback behavior, alpha weighting, bounds & rounding
- extract_confidence_and_fusion: integration on analysis dict

Note: We avoid external dependencies; tests should run fast and deterministically.
"""
import math
import os

import pytest

# Make import robust whether tests run from repo root or backend directory
try:
    from services.confidence_fusion import (
        parse_ai_confidence,
        compute_fusion_score,
        extract_confidence_and_fusion,
        CONF_FUSION_ALPHA,
    )
except ModuleNotFoundError:  # pragma: no cover - fallback for different CWDs
    import sys
    from pathlib import Path

    backend_dir = Path(__file__).resolve().parents[1]
    sys.path.append(str(backend_dir))
    from services.confidence_fusion import (
        parse_ai_confidence,
        compute_fusion_score,
        extract_confidence_and_fusion,
        CONF_FUSION_ALPHA,
    )


@pytest.mark.parametrize(
    "text, expected_val, expected_raw_contains",
    [
        ("建议买入（信心8/10）", 8.0, "信心8/10"),
        ("confidence: 7.5/10", 7.5, "confidence: 7.5/10"),
        ("信心：９/１０", 9.0, "信心：９/１０"),
        ("最终建议：买入（信心十/10）", None, None),  # 中文数字无法解析
        ("信心12/10", 10.0, "信心12/10"),  # 超界截断到10
        ("信心-1/10", 0.0, "信心-1/10"),  # 负数截断到0
        ("无信心提及", None, None),
        ("", None, None),
        (None, None, None),
        (12345, None, None),  # 非字符串
        ("(confidence 6)", 6.0, "confidence 6"),  # 括号英文简写
        ("（信心 8.25/10）更多说明\n下一行", 8.25, "信心 8.25/10"),
    ],
)
def test_parse_ai_confidence(text, expected_val, expected_raw_contains):
    val, raw = parse_ai_confidence(text) if isinstance(text, str) or text is None else parse_ai_confidence(text)  # keep call uniform
    if expected_val is None:
        assert val is None and raw is None
    else:
        assert pytest.approx(val, rel=0, abs=1e-9) == expected_val
        assert raw is not None and (expected_raw_contains in raw)


@pytest.mark.parametrize(
    "tech, ai, alpha, expected",
    [
        (0.8, 9.0, 0.4, 8.6),  # 0.4*8 + 0.6*9 = 8.6
        (0.5, None, 0.4, 5.0),  # 无AI回退技术分：0.5*10 = 5.0
        (None, 8.0, 0.4, None),  # 技术分为空
        (0.75, 8.5, 0.3, 8.2),  # 0.3*7.5 + 0.7*8.5 = 8.2
        (1.2, 3.0, 0.5, 6.5),   # tech>1 映射12→裁剪到10：0.5*10 + 0.5*3 = 6.5
        (-0.1, 9.0, 0.5, 4.5),  # tech<0 映射-1→裁剪到0：0.5*0 + 0.5*9 = 4.5
        (0.3333, 0.0, 0.4, 1.33),  # 0.4*3.333 + 0.6*0 = 1.333 → 1.33
    ],
)
def test_compute_fusion_score(tech, ai, alpha, expected):
    result = compute_fusion_score(tech, ai, alpha)
    if expected is None:
        assert result is None
    else:
        assert pytest.approx(result, rel=0, abs=1e-9) == expected
        # 范围保护
        assert 0.0 <= result <= 10.0
        # 两位小数（以字符串格式检查）
        s = f"{result:.2f}"
        assert len(s.split(".")[-1]) == 2


def test_extract_confidence_and_fusion_integration():
    analysis = {"score": 0.7}
    advice = "建议持有（信心 8/10）。理由：基本面稳健。"
    updated = extract_confidence_and_fusion(analysis, advice)
    assert "ai_confidence" in updated and "fusion_score" in updated and "ai_confidence_raw" in updated
    assert pytest.approx(updated["ai_confidence"], rel=0, abs=1e-9) == 8.0
    # 默认 alpha 来自环境或默认0.4
    alpha = CONF_FUSION_ALPHA
    expected = round(alpha * (0.7 * 10.0) + (1 - alpha) * 8.0, 2)
    assert pytest.approx(updated["fusion_score"], rel=0, abs=1e-9) == expected


def test_extract_fallback_when_no_ai_confidence():
    analysis = {"score": 0.42}
    advice = "未提供信心说明。"
    updated = extract_confidence_and_fusion(analysis, advice)
    assert updated["ai_confidence"] is None
    assert updated["ai_confidence_raw"] is None
    assert pytest.approx(updated["fusion_score"], rel=0, abs=1e-9) == round(0.42 * 10.0, 2)