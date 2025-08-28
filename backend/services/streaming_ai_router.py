"""
流式AI路由器
支持流式调用OpenAI、DeepSeek、Gemini等AI提供商
用于实现实时推荐过程展示
"""
from typing import Literal, Optional, AsyncGenerator, Iterator
import os
import json
import asyncio
import aiohttp
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

Provider = Literal["openai", "deepseek", "gemini"]

class StreamingAIRequest(BaseModel):
    prompt: str
    provider: Optional[Provider] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    api_key: Optional[str] = None
    stream: bool = True

class StreamingAIRouter:
    """流式AI路由器，支持实时数据流"""
    
    def __init__(self):
        self.default_provider: Provider = os.getenv("DEFAULT_AI_PROVIDER", "deepseek")  # type: ignore
        
    def _get_temperature(self, temperature: Optional[float]) -> float:
        """获取温度参数，带默认值"""
        return temperature if temperature is not None else 0.3
    
    async def stream_complete(self, prompt: str, provider: Optional[Provider] = None, 
                             model: Optional[str] = None, temperature: Optional[float] = None, 
                             api_key: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        流式完成AI请求
        
        Args:
            prompt: 提示词
            provider: AI提供商
            model: 模型名称
            temperature: 温度参数
            api_key: API密钥
            
        Yields:
            str: 流式返回的文本块
        """
        provider = provider or self.default_provider
        
        print(f"🔄 开始流式AI请求 - Provider: {provider}, Model: {model}")
        
        try:
            if provider == "openai":
                async for chunk in self._openai_stream_complete(prompt, model, temperature, api_key):
                    yield chunk
            elif provider == "deepseek":
                async for chunk in self._deepseek_stream_complete(prompt, model, temperature, api_key):
                    yield chunk
            elif provider == "gemini":
                async for chunk in self._gemini_stream_complete(prompt, model, temperature, api_key):
                    yield chunk
            else:
                yield f"❌ 不支持的AI提供商: {provider}"
                
        except Exception as e:
            yield f"❌ AI流式请求失败: {str(e)}"
            
    async def _openai_stream_complete(self, prompt: str, model: Optional[str] = None, 
                                     temperature: Optional[float] = None, api_key: Optional[str] = None) -> AsyncGenerator[str, None]:
        """OpenAI流式完成"""
        try:
            from openai import AsyncOpenAI
            
            key = api_key or os.getenv("OPENAI_API_KEY")
            if not key:
                yield "❌ OpenAI API Key 未配置"
                return
                
            client = AsyncOpenAI(api_key=key)
            mdl = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            temp = self._get_temperature(temperature)
            
            stream = await client.chat.completions.create(
                model=mdl,
                messages=[{"role": "user", "content": prompt}],
                temperature=temp,
                stream=True
            )
            
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
                    
        except Exception as e:
            yield f"❌ OpenAI流式请求失败: {str(e)}"
    
    async def _deepseek_stream_complete(self, prompt: str, model: Optional[str] = None, 
                                       temperature: Optional[float] = None, api_key: Optional[str] = None) -> AsyncGenerator[str, None]:
        """DeepSeek流式完成"""
        try:
            key = api_key or os.getenv("DEEPSEEK_API_KEY")
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            mdl = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            
            if not key:
                yield "❌ DeepSeek API Key 未配置"
                return
                
            url = f"{base_url}/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": mdl,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self._get_temperature(temperature),
                "stream": True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        yield f"❌ DeepSeek API请求失败: {response.status}"
                        return
                        
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]  # 移除 'data: ' 前缀
                            
                            if data_str == '[DONE]':
                                break
                                
                            try:
                                data = json.loads(data_str)
                                content = data.get('choices', [{}])[0].get('delta', {}).get('content')
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            yield f"❌ DeepSeek流式请求失败: {str(e)}"
    
    async def _gemini_stream_complete(self, prompt: str, model: Optional[str] = None, 
                                     temperature: Optional[float] = None, api_key: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Gemini流式完成"""
        try:
            import google.generativeai as genai
            
            key = api_key or os.getenv("GEMINI_API_KEY")
            if not key:
                yield "❌ Gemini API Key 未配置"
                return
                
            genai.configure(api_key=key)
            mdl = model or os.getenv("GEMINI_MODEL", "gemini-pro")
            model_obj = genai.GenerativeModel(mdl)
            
            generation_config = {
                "temperature": self._get_temperature(temperature)
            }
            
            # Gemini的流式接口使用方式
            response = model_obj.generate_content(
                prompt, 
                generation_config=generation_config,
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            yield f"❌ Gemini流式请求失败: {str(e)}"
    
    async def complete_sync(self, req: StreamingAIRequest) -> str:
        """
        同步方式完成AI请求（兼容原有接口）
        """
        full_response = ""
        async for chunk in self.stream_complete(
            req.prompt, req.provider, req.model, req.temperature, req.api_key
        ):
            full_response += chunk
        return full_response
    
    def complete_sync_blocking(self, req: StreamingAIRequest) -> str:
        """
        阻塞式同步完成AI请求（兼容原有非异步代码）
        """
        try:
            # 在已有事件循环中运行
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 创建新的任务
                task = asyncio.create_task(self.complete_sync(req))
                return asyncio.run_coroutine_threadsafe(self.complete_sync(req), loop).result()
            else:
                return asyncio.run(self.complete_sync(req))
        except RuntimeError:
            # 如果没有事件循环，创建新的
            return asyncio.run(self.complete_sync(req))

class ProgressManager:
    """任务进度管理器"""
    
    def __init__(self):
        self.progress_callbacks = {}
        
    def register_callback(self, task_id: str, callback):
        """注册进度回调函数"""
        self.progress_callbacks[task_id] = callback
        
    def unregister_callback(self, task_id: str):
        """注销进度回调函数"""
        if task_id in self.progress_callbacks:
            del self.progress_callbacks[task_id]
    
    async def update_progress(self, task_id: str, progress: float):
        """更新任务进度"""
        if task_id in self.progress_callbacks:
            try:
                await self.progress_callbacks[task_id]({
                    'type': 'progress',
                    'task_id': task_id,
                    'progress': progress,
                    'timestamp': asyncio.get_event_loop().time()
                })
            except Exception as e:
                print(f"❌ 进度回调失败: {e}")
    
    async def update_current_symbol(self, task_id: str, symbol: str):
        """更新当前处理的股票"""
        if task_id in self.progress_callbacks:
            try:
                await self.progress_callbacks[task_id]({
                    'type': 'current_symbol',
                    'task_id': task_id,
                    'symbol': symbol,
                    'timestamp': asyncio.get_event_loop().time()
                })
            except Exception as e:
                print(f"❌ 符号更新回调失败: {e}")
    
    async def push_ai_chunk(self, task_id: str, symbol: str, chunk: str, accumulated: str):
        """推送AI数据块"""
        if task_id in self.progress_callbacks:
            try:
                await self.progress_callbacks[task_id]({
                    'type': 'ai_chunk',
                    'task_id': task_id,
                    'symbol': symbol,
                    'chunk': chunk,
                    'accumulated': accumulated,
                    'timestamp': asyncio.get_event_loop().time()
                })
            except Exception as e:
                print(f"❌ AI块推送回调失败: {e}")
    
    async def record_symbol_completed(self, task_id: str, symbol: str):
        """记录股票分析完成"""
        if task_id in self.progress_callbacks:
            try:
                await self.progress_callbacks[task_id]({
                    'type': 'symbol_completed',
                    'task_id': task_id,
                    'symbol': symbol,
                    'timestamp': asyncio.get_event_loop().time()
                })
            except Exception as e:
                print(f"❌ 完成记录回调失败: {e}")
    
    async def record_symbol_failed(self, task_id: str, symbol: str, error: str):
        """记录股票分析失败"""
        if task_id in self.progress_callbacks:
            try:
                await self.progress_callbacks[task_id]({
                    'type': 'symbol_failed',
                    'task_id': task_id,
                    'symbol': symbol,
                    'error': error,
                    'timestamp': asyncio.get_event_loop().time()
                })
            except Exception as e:
                print(f"❌ 失败记录回调失败: {e}")
                
    async def update_phase(self, task_id: str, phase: str):
        """更新任务阶段"""
        if task_id in self.progress_callbacks:
            try:
                await self.progress_callbacks[task_id]({
                    'type': 'phase_change',
                    'task_id': task_id,
                    'phase': phase,
                    'timestamp': asyncio.get_event_loop().time()
                })
            except Exception as e:
                print(f"❌ 阶段更新回调失败: {e}")
    
    async def record_ai_analysis_start(self, task_id: str, symbol: str):
        """记录AI分析开始"""
        if task_id in self.progress_callbacks:
            try:
                await self.progress_callbacks[task_id]({
                    'type': 'ai_analysis_start',
                    'task_id': task_id,
                    'symbol': symbol,
                    'timestamp': asyncio.get_event_loop().time()
                })
            except Exception as e:
                print(f"❌ AI分析开始回调失败: {e}")
    
    async def record_symbol_analysis_complete(self, task_id: str, symbol: str, result: dict):
        """记录股票分析完成"""
        if task_id in self.progress_callbacks:
            try:
                await self.progress_callbacks[task_id]({
                    'type': 'symbol_analysis_complete',
                    'task_id': task_id,
                    'symbol': symbol,
                    'result': result,
                    'timestamp': asyncio.get_event_loop().time()
                })
            except Exception as e:
                print(f"❌ 分析完成回调失败: {e}")

# 全局进度管理器实例
progress_manager = ProgressManager()