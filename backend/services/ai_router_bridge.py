"""
AI路由器桥接层
确保新的流式AI路由器与原有系统的兼容性
"""
import asyncio
from typing import Optional, Dict, Any
from .ai_router import AIRouter, AIRequest  # 原有的AI路由器
from .streaming_ai_router import StreamingAIRouter, StreamingAIRequest  # 新的流式AI路由器

class UnifiedAIRouter:
    """统一的AI路由器，支持同步和异步调用"""
    
    def __init__(self):
        self.legacy_router = AIRouter()  # 原有的同步路由器
        self.streaming_router = StreamingAIRouter()  # 新的流式路由器
    
    def complete(self, req: AIRequest) -> str:
        """同步完成（兼容原有代码）"""
        # 转换为流式请求
        streaming_req = StreamingAIRequest(
            prompt=req.prompt,
            provider=req.provider,
            model=req.model,
            temperature=req.temperature,
            api_key=req.api_key,
            stream=False
        )
        
        try:
            # 使用新的流式路由器的同步方法
            return self.streaming_router.complete_sync_blocking(streaming_req)
        except Exception as e:
            print(f"⚠️ 流式路由器失败，回退到原有路由器: {e}")
            # 回退到原有路由器
            return self.legacy_router.complete(req)
    
    async def complete_async(self, req: AIRequest) -> str:
        """异步完成"""
        streaming_req = StreamingAIRequest(
            prompt=req.prompt,
            provider=req.provider,
            model=req.model,
            temperature=req.temperature,
            api_key=req.api_key,
            stream=False
        )
        
        return await self.streaming_router.complete_sync(streaming_req)
    
    async def stream_complete(self, req: AIRequest):
        """流式完成"""
        async for chunk in self.streaming_router.stream_complete(
            req.prompt, req.provider, req.model, req.temperature, req.api_key
        ):
            yield chunk

# 创建全局统一路由器实例
unified_ai_router = UnifiedAIRouter()

# 为了向后兼容，我们可以monkey patch原有的AIRouter
def patch_existing_ai_router():
    """修补现有的AI路由器以使用新的统一路由器"""
    import sys
    from . import ai_router
    
    # 保存原有的类
    original_ai_router = ai_router.AIRouter
    
    class PatchedAIRouter(original_ai_router):
        def __init__(self):
            super().__init__()
            self.unified_router = unified_ai_router
        
        def complete(self, req: AIRequest) -> str:
            try:
                return self.unified_router.complete(req)
            except Exception as e:
                print(f"⚠️ 统一路由器失败，使用原始实现: {e}")
                return super().complete(req)
    
    # 替换原有的类
    ai_router.AIRouter = PatchedAIRouter
    
    print("✅ AI路由器已修补以支持流式功能")

# 自动应用修补
try:
    patch_existing_ai_router()
except Exception as e:
    print(f"⚠️ AI路由器修补失败: {e}")