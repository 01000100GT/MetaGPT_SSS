from typing import Any, Optional
from pydantic import ConfigDict, Field, model_validator
import logging

from .action import Action
from src.multiagent.provider.llm_factory import create_llm
from src.multiagent.provider.base_llm import BaseLLM
from src.multiagent.llm_configs.llm_config import LLMConfig
from pathlib import Path

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class LLMChatAction(Action):
    """基于LLM的聊天动作"""
    name: str = Field(default="LLM聊天")
    desc: str = Field(default="使用大语言模型进行对话")
    llm_config: Optional[LLMConfig] = Field(default=None, description="LLM配置")
    system_prompt: str = Field(default="你是一个有用的AI助手。", description="系统提示词")
    prompt_template: str = Field(default="{input}", description="提示词模板")
    max_tokens: int = Field(default=2000, description="最大生成token数")
    temperature: float = Field(default=0.7, description="温度参数")
    stream: bool = Field(default=False, description="是否流式输出")

    # 新增类属性
    _DEFAULT_CONFIG_PATH = Path.home() / ".metagpt" / "config2.yaml"
    # 添加模型配置，允许任意类型和私有属性
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, llm_config: Optional[LLMConfig] = None, system_prompt: Optional[str] = None, **data):
        super().__init__(**data)
        # 初始化_llm属性
        self._llm = None

        # 自动加载默认配置
        if llm_config is None:
            if self._DEFAULT_CONFIG_PATH.exists():
                llm_config = LLMConfig.load_from_yaml(
                    self._DEFAULT_CONFIG_PATH)
            else:
                raise FileNotFoundError(
                    f"默认配置文件未找到: {self._DEFAULT_CONFIG_PATH}")

        # 强制创建有效LLM实例
        self._llm = create_llm(llm_config or LLMConfig())  # 添加默认配置
        # 类型校验确保接口实现
        if not isinstance(self._llm, BaseLLM):
            raise ValueError("LLM实例未正确实现BaseLLM接口")

        if system_prompt:
            self._system_prompt = system_prompt

    @model_validator(mode="after")
    def validate_action(self):
        """验证动作配置"""
        # 检查_llm属性是否存在，如果不存在则初始化
        if not hasattr(self, '_llm') or self._llm is None:
            self._llm = create_llm(self.llm_config or LLMConfig())
        return self

    def format_prompt(self, input_text: str, **kwargs) -> str:
        """格式化提示词"""
        # 替换模板中的变量
        context = {"input": input_text, **kwargs}
        return self.prompt_template.format(**context)

    async def run(self, input_text: str = "", **kwargs) -> str:
        """执行LLM聊天动作"""
        try:
            # 格式化提示词
            prompt = self.format_prompt(input_text, **kwargs)

            # 准备消息列表
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]

            # 添加历史消息（如果有）
            if "history" in kwargs and kwargs["history"]:
                # 插入到系统消息和用户消息之间
                messages = [messages[0]] + kwargs["history"] + [messages[-1]]

            # 调用LLM
            if self.stream:
                # 流式输出
                response_text = ""
                # 确保_llm不为None
                if self._llm is None:
                    self._llm = create_llm(self.llm_config or LLMConfig())
                try:
                    # 使用await获取异步生成器
                    async for chunk in await self._llm.astream(
                        messages=messages,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature
                    ):
                        response_text += chunk
                        # 如果需要实时处理，可以在这里添加回调
                except Exception as e:
                    logger.error(f"流式生成失败: {str(e)}")
                    return f"流式生成错误: {str(e)}"

                return response_text
            else:
                # 普通输出
                # 确保_llm不为None
                if self._llm is None:
                    self._llm = create_llm(self.llm_config or LLMConfig())

                try:
                    response = await self._llm.agenerate(
                        messages=messages,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature
                    )
                    return response
                except Exception as e:
                    logger.error(f"生成回复失败: {str(e)}")
                    return f"生成回复错误: {str(e)}"

        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}")
            return f"LLM调用错误: {str(e)}"

    async def aask(self, prompt: str, system_prompt: str | None = None, **kwargs) -> str:
        """简化版LLM调用"""
        # 临时覆盖系统提示词
        original_system_prompt = self.system_prompt
        if system_prompt:
            self.system_prompt = system_prompt

        try:
            return await self.run(prompt, **kwargs)
        finally:
            # 恢复原始系统提示词
            if system_prompt:
                self.system_prompt = original_system_prompt
