# 添加 from __future__ import annotations 解决类型注解的延迟评估问题
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
import logging

from src.multiagent.llm_configs.llm_config import LLMConfig

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class BaseLLM(ABC):
    """LLM基础接口类"""

    @abstractmethod
    async def agenerate(self, messages: List[Dict[str, str]], max_tokens: int = 2000, temperature: float = 0.7, **kwargs) -> str:
        """异步生成回复

        Args:
            messages: 消息列表，格式为[{"role": "user", "content": "你好"}]
            max_tokens: 最大生成token数
            temperature: 温度参数，控制随机性
            **kwargs: 其他参数

        Returns:
            str: 生成的回复文本
        """
        pass

    @abstractmethod
    async def astream(self, messages: List[Dict[str, str]], max_tokens: int = 2000, temperature: float = 0.7, **kwargs) -> AsyncGenerator[str, None]:
        """异步流式生成回复

        Args:
            messages: 消息列表，格式为[{"role": "user", "content": "你好"}]
            max_tokens: 最大生成token数
            temperature: 温度参数，控制随机性
            **kwargs: 其他参数
 
        """
        pass

    def generate(self, messages: List[Dict[str, str]], max_tokens: int = 2000, temperature: float = 0.7, **kwargs) -> str:
        """同步生成回复（默认实现，调用异步方法）

        Args:
            messages: 消息列表
            max_tokens: 最大生成token数
            temperature: 温度参数
            **kwargs: 其他参数

        Returns:
            str: 生成的回复文本
        """
        import asyncio
        return asyncio.run(self.agenerate(messages, max_tokens, temperature, **kwargs))

    def __init__(self, config: LLMConfig):
        self.config = config
        self.model = config.model

    @abstractmethod
    async def acompletion(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """异步调用LLM获取回复"""
        pass

    @abstractmethod
    async def acompletion_stream(self, messages: List[Dict], **kwargs) -> AsyncGenerator[str, None]:
        """异步流式调用LLM获取回复"""
        # 在抽象方法中添加 yield "" 占位语句，避免抽象类实例化时报错
        yield ""  # 添加空生成器避免抽象方法报错
        # 实际实现应该在子类中覆盖这个方法

    async def acompletion_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """异步调用LLM获取纯文本回复"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.acompletion(messages)
        # 添加错误处理
        if "error" in response:
            logger.error(f"LLM调用失败: {response['error']}")
            return f"LLM服务错误: {response['error']}"
        return self.get_choice_text(response)

    def get_choice_text(self, response: Dict) -> str:
        """从响应中提取文本"""
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            logger.error(f"提取响应文本失败: {e}")
            return ""
