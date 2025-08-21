#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试全市场推荐API
"""
import requests
import json
import os

# 设置后端地址
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:8000')

def test_health():
    """健康检查"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        print(f"✅ 健康检查: {response.status_code} - {response.text}")
        return True
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False

def test_market_recommend():
    """测试全市场推荐接口"""
    try:
        # 小样本测试（10个候选，避免超时）
        payload = {
            "period": "6mo",
            "max_candidates": 10,
            "weights": {
                "technical": 0.5,
                "macro_sentiment": 0.3,
                "news_events": 0.2
            },
            "exclude_st": True,
            "min_market_cap": 50  # 50亿市值以上
        }
        
        print("🔄 正在调用全市场推荐API...")
        response = requests.post(
            f"{BACKEND_URL}/api/recommend/market", 
            json=payload, 
            timeout=120
        )
        
        print(f"📊 全市场推荐状态: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 推荐成功!")
            print(f"📝 推荐ID: {result.get('rec_id')}")
            print(f"📈 推荐数量: {len(result.get('recommendations', []))}")
            print(f"🔍 筛选总数: {result.get('total_screened', 'N/A')}")
            print(f"⚖️ 权重配置: {result.get('weights_used', {})}")
            
            # 展示前3个推荐
            recommendations = result.get('recommendations', [])[:3]
            for i, rec in enumerate(recommendations, 1):
                print(f"\n🏆 推荐{i}: {rec.get('stock_name', 'N/A')} ({rec.get('stock_code', 'N/A')})")
                print(f"   💡 建议: {rec.get('action', 'N/A')}")
                print(f"   📄 理由: {rec.get('reason_brief', 'N/A')[:100]}...")
        else:
            print(f"❌ 请求失败: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ 全市场推荐测试失败: {e}")

def main():
    print("🚀 开始测试全市场推荐功能...")
    print("=" * 50)
    
    # 健康检查
    if not test_health():
        print("❌ 后端服务不可用，请先启动后端服务")
        return
    
    print("\n" + "=" * 50)
    
    # 测试全市场推荐
    test_market_recommend()
    
    print("\n" + "=" * 50)
    print("✨ 测试完成!")

if __name__ == "__main__":
    main()