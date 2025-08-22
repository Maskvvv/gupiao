from typing import Literal, Optional
import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

Provider = Literal["openai", "deepseek", "gemini"]

class AIRequest(BaseModel):
    prompt: str
    provider: Optional[Provider] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    api_key: Optional[str] = None

class AIRouter:
    def __init__(self):
        self.default_provider: Provider = os.getenv("DEFAULT_AI_PROVIDER", "deepseek")  # type: ignore
    
    def _get_temperature(self, temperature: Optional[float]) -> float:
        """获取温度参数，带默认值"""
        return temperature if temperature is not None else 0.3

    def _openai_complete(self, prompt: str, model: Optional[str] = None, temperature: Optional[float] = None, api_key: Optional[str] = None) -> str:
        from openai import OpenAI

        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            return "OpenAI API Key 未配置"
        client = OpenAI(api_key=key)
        mdl = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        temp = self._get_temperature(temperature)
        resp = client.chat.completions.create(
            model=mdl,
            messages=[{"role": "user", "content": prompt}],
            temperature=temp,
        )
        return resp.choices[0].message.content or ""

    def _deepseek_complete(self, prompt: str, model: Optional[str] = None, temperature: Optional[float] = None, api_key: Optional[str] = None) -> str:
        import requests

        key = api_key or os.getenv("DEEPSEEK_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        mdl = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        if not key:
            return "DeepSeek API Key 未配置"
        url = f"{base_url}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {
            "model": mdl,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self._get_temperature(temperature),
        }
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    def _gemini_complete(self, prompt: str, model: Optional[str] = None, temperature: Optional[float] = None, api_key: Optional[str] = None) -> str:
        import google.generativeai as genai

        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            return "Gemini API Key 未配置"
        genai.configure(api_key=key)
        mdl = model or os.getenv("GEMINI_MODEL", "gemini-pro")
        model_obj = genai.GenerativeModel(mdl)
        generation_config = {"temperature": self._get_temperature(temperature)}
        resp = model_obj.generate_content(prompt, generation_config=generation_config)
        return resp.text or ""

    def complete(self, req: AIRequest) -> str:
        provider: Provider = req.provider or self.default_provider
        print(f"--------------------------------------------------------------------")
        print(f"正在使用 {provider} 处理请求")
        print(f"请求参数: prompt={req.prompt}, model={req.model}, temperature={req.temperature}")
        
        do = {
            "openai": lambda: self._openai_complete(req.prompt, req.model, req.temperature, req.api_key),
            "deepseek": lambda: self._deepseek_complete(req.prompt, req.model, req.temperature, req.api_key),
            "gemini": lambda: self._gemini_complete(req.prompt, req.model, req.temperature, req.api_key),
        }
        
        result = do.get(provider, lambda: "不支持的AI提供商")()
        print(f"处理完成，结果长度: {result}")
        print(f"--------------------------------------------------------------------")
        return result
