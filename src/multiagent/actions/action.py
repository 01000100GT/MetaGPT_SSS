
from pydantic import BaseModel, Field, model_validator
from typing import Dict, Optional, Any, List, Tuple
import asyncio
import logging

# 在Action类定义前添加logger配置
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

class Action(BaseModel):
    """动作基类 """
    name: str = Field(default="BasicAction")
    desc: str = Field(default="基础动作")
    context: Optional[Dict] = Field(default=None, exclude=True)

    # 添加依赖动作
    dependencies: List[str] = Field(
        default_factory=list, description="依赖的其他动作")

    # 添加前置条件和后置条件
    preconditions: List[str] = Field(
        default_factory=list, description="执行前置条件")
    postconditions: List[str] = Field(
        default_factory=list, description="执行后置条件")

    # 添加重试机制
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_delay: float = Field(default=1.0, description="重试延迟(秒)")

    @model_validator(mode="after")
    def validate_action(self):
        """验证动作配置"""
        return self

    @property
    def agent_description(self):
        """动作描述"""
        return f"{self.name}: {self.desc}"

    @property
    def set_get_context(self):
        """动作上下文

        这个属性方法用于获取和设置动作的上下文信息(_context)
        上下文信息可以包含执行动作时需要的各种状态和数据
        使用@property装饰器使得这个方法可以像属性一样被访问

        Returns:
            Dict: 返回动作的上下文字典，如果未设置则返回None
        """
        return self.context

    async def run(self, *args, **kwargs) -> Any:
        """执行动作"""
        raise NotImplementedError("子类必须实现run方法")

    async def run_with_retry(self, *args, **kwargs) -> Any:
        """带重试机制的执行动作"""
        retries = 0
        last_error = None

        while retries < self.max_retries:
            try:
                return await self.run(*args, **kwargs)
            except Exception as e:
                last_error = e
                retries += 1
                if retries < self.max_retries:
                    logger.warning(
                        f"动作 {self.name} 执行失败，将在 {self.retry_delay} 秒后重试 ({retries}/{self.max_retries}): {str(e)}")
                    await asyncio.sleep(self.retry_delay)

        logger.error(
            f"动作 {self.name} 在 {self.max_retries} 次尝试后仍然失败: {str(last_error)}")
        if last_error is not None:
            raise last_error
        else:
            raise RuntimeError(f"动作 {self.name} 执行失败，但未捕获到具体异常")

    def check_preconditions(self, context: Dict[str, Any]) -> Tuple[bool, str]:
        """检查前置条件

        Returns:
            Tuple[bool, str]: (是否满足条件, 不满足的原因)
        """
        # 实际项目中可以实现更复杂的条件检查逻辑
        return True, ""
