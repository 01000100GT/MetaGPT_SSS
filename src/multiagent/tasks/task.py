from typing import List, Optional, Dict, Any, Callable
from pydantic import BaseModel, Field
from src.multiagent.roles.role import Role
from src.multiagent.schema.message import Message
import asyncio
import logging

# 在Action类定义前添加logger配置
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")
# 任务依赖管理


class Task(BaseModel):
    """任务类，管理角色执行和依赖关系"""
    description: str
    agent: Role
    dependencies: List["Task"] = Field(default_factory=list)
    result: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed

    # 添加任务优先级
    priority: int = Field(default=0, description="任务优先级，数值越大优先级越高")

    # 添加超时控制
    timeout: Optional[float] = Field(default=None, description="任务执行超时时间(秒)")

    # 添加任务重试配置
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_delay: float = Field(default=1.0, description="重试延迟(秒)")

    # 添加任务回调
    on_success: Optional[Callable] = Field(
        default=None, exclude=True, description="任务成功回调")
    on_failure: Optional[Callable] = Field(
        default=None, exclude=True, description="任务失败回调")

    async def execute(self, context: Optional[Dict[str, Any]] = None) -> str:
        """执行任务，确保依赖任务已完成"""
        # 等待所有依赖任务完成
        for dep in self.dependencies:
            if dep.status != "completed":
                await dep.execute()

        self.status = "running"
        retries = 0
        last_error = None

        while retries <= self.max_retries:
            try:
                # 设置超时
                if self.timeout:
                    # 将依赖任务的结果作为上下文传递
                    ctx = context or {}
                    for dep in self.dependencies:
                        if dep.result:
                            ctx[dep.description] = dep.result

                    # 使用asyncio.wait_for实现超时控制
                    self.result = await asyncio.wait_for(
                        self.agent.run(with_message=self.description),
                        timeout=self.timeout
                    )
                else:
                    # 无超时版本
                    ctx = context or {}
                    for dep in self.dependencies:
                        if dep.result:
                            ctx[dep.description] = dep.result

                    self.result = await self.agent.run(with_message=self.description)

                self.status = "completed"

                # 调用成功回调
                if self.on_success:
                    await self.on_success(self)

                return self.result

            except asyncio.TimeoutError:
                logger.warning(f"任务 '{self.description}' 执行超时")
                last_error = TimeoutError(f"任务执行超时: {self.timeout}秒")
                break  # 超时直接失败，不重试

            except Exception as e:
                last_error = e
                retries += 1
                if retries <= self.max_retries:
                    logger.warning(
                        f"任务 '{self.description}' 执行失败，将在 {self.retry_delay} 秒后重试 ({retries}/{self.max_retries}): {str(e)}")
                    await asyncio.sleep(self.retry_delay)
                else:
                    break

        # 所有重试都失败
        self.status = "failed"
        logger.error(f"任务 '{self.description}' 执行失败: {str(last_error)}")

        # 调用失败回调
        if self.on_failure:
            await self.on_failure(self, last_error)

        raise last_error or Exception(f"任务 '{self.description}' 执行失败")
