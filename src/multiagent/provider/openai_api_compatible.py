import json
import aiohttp
from typing import List, Dict, Any, AsyncGenerator, Optional
import logging
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from .base_llm import BaseLLM
from src.multiagent.llm_configs.llm_config import LLMConfig, LLMType

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class OpenAI_API_COMPATIBLE_LLM(BaseLLM):
    """OpenAI兼容的LLM提供者"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.headers = {
            "Content-Type": "application/json"
        }
        if config.api_key:
            self.headers["Authorization"] = f"Bearer {config.api_key}"

    def _get_proxy_params(self) -> Dict:
        """获取代理参数"""
        if self.config.proxy:
            return {"proxy": self.config.proxy}
        return {}

    def _construct_payload(self, messages: List[Dict], stream: bool = False) -> Dict:
        """构造请求负载"""
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": stream
        }
        # 添加额外参数
        payload.update(self.config.extra_params)
        return payload

    def get_choice_text(self, response: Dict[str, Any]) -> str:
        """从响应中提取文本内容"""
        if "error" in response:
            return f"LLM调用错误: {response['error']}"

        if "choices" in response and len(response["choices"]) > 0:
            return response["choices"][0]["message"]["content"]

        return "无有效响应内容"

    # 添加重试机制
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def acompletion(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """异步调用LLM获取回复"""
        timeout = kwargs.get("timeout", self.config.timeout)
        payload = self._construct_payload(messages)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=timeout,
                    **self._get_proxy_params()
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            f"LLM API错误: {response.status}, {error_text}")
                        return {"error": error_text, "choices": [{"message": {"content": f"API错误: {response.status}"}}]}

                    return await response.json()
        except Exception as e:
            logger.error(f"LLM调用异常: {str(e)}")
            return {"error": str(e), "choices": [{"message": {"content": f"调用异常: {str(e)}"}}]}

    async def acompletion_stream(self, messages: List[Dict], **kwargs) -> AsyncGenerator[str, None]:
        """异步流式调用LLM获取回复"""
        timeout = kwargs.get("timeout", self.config.timeout)
        payload = self._construct_payload(messages, stream=True)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=timeout,
                    **self._get_proxy_params()
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            f"LLM API流式调用错误: {response.status}, {error_text}")
                        yield f"API错误: {response.status}"
                        return

                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if not line:
                            continue
                        if line == "data: [DONE]":
                            break
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                if "choices" in data and data["choices"]:
                                    content = data["choices"][0].get(
                                        "delta", {}).get("content", "")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                logger.warning(f"无法解析流式响应: {line}")
        except Exception as e:
            logger.error(f"LLM流式调用异常: {str(e)}")
            yield f"调用异常: {str(e)}"

    async def agenerate(self, messages: List[Dict[str, str]], max_tokens: int = 2000, temperature: float = 0.7, **kwargs) -> str:
        """实现BaseLLM的agenerate抽象方法"""
        response = await self.acompletion(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
        return self.get_choice_text(response)

    async def astream(self, messages: List[Dict[str, str]], max_tokens: int = 2000, temperature: float = 0.7, **kwargs) -> AsyncGenerator[str, None]:
        """实现BaseLLM的astream抽象方法"""
        return self._astream_impl(messages, max_tokens, temperature, **kwargs)

    async def _astream_impl(self, messages: List[Dict[str, str]], max_tokens: int, temperature: float, **kwargs) -> AsyncGenerator[str, None]:
        """实现BaseLLM的astream抽象方法"""
        async for chunk in self.acompletion_stream(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        ):
            yield chunk
