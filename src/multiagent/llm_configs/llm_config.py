from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import yaml
from pathlib import Path


class LLMType(str, Enum):
    """LLM类型枚举"""
    OPENAI = "openai"
    OPENAI_API_COMPATIBLE = "OpenAI-API-Compatible"  # 本地LLM


class LLMConfig(BaseModel):
    """LLM配置类"""
    api_type: LLMType = Field(default=LLMType.OPENAI_API_COMPATIBLE)
    model: str = Field(default="modelid")
    api_key: Optional[str] = Field(default=None)
    base_url: str = Field(default="http://localhost:8000/v1")
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2000)
    timeout: int = Field(default=120)
    proxy: Optional[str] = Field(default=None)
    stream: bool = Field(default=True)
    extra_params: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def load_from_yaml(cls, path: Path) -> "LLMConfig":
        with open(path, 'r') as f:
            config_data = yaml.safe_load(f)
        return cls(**config_data.get("llm", {}))

    @classmethod
    def local_llm(cls, base_url: str = "http://localhost:8000/v1"):
        """快速创建本地LLM配置"""
        return cls(
            api_type=LLMType.OPENAI_API_COMPATIBLE,
            base_url=base_url,
            model="local-model",
            temperature=0.7
        )
