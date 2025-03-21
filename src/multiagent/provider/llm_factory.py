from typing import Dict, Type, Optional
import logging

from .base_llm import BaseLLM
from .openai_api_compatible import OpenAI_API_COMPATIBLE_LLM
from src.multiagent.llm_configs.llm_config import LLMConfig, LLMType

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

# LLM提供者注册表
LLM_REGISTRY: Dict[LLMType, Type[BaseLLM]] = {
    LLMType.OPENAI: OpenAI_API_COMPATIBLE_LLM,
    LLMType.OPENAI_API_COMPATIBLE: OpenAI_API_COMPATIBLE_LLM,  # 本地LLM也使用OpenAI兼容接口
}


def create_llm(config: Optional[LLMConfig] = None) -> BaseLLM:
    """创建LLM实例"""
    if config is None:
        config = LLMConfig()

    llm_cls = LLM_REGISTRY.get(config.api_type)
    if not llm_cls:
        logger.warning(f"未知的LLM类型: {config.api_type}，使用默认OpenAI兼容接口")
        llm_cls = OpenAI_API_COMPATIBLE_LLM

    return llm_cls(config)
