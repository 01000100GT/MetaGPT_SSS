from pydantic import BaseModel, Field, ConfigDict
from functools import lru_cache
from typing import List, Dict, Any, Optional, Callable, Awaitable, TYPE_CHECKING
from enum import Enum
from src.multiagent.actions.action import Action
from src.multiagent.schema.message import Message
import logging
# 使用TYPE_CHECKING条件导入，避免循环导入
if TYPE_CHECKING:
    from src.multiagent.environment.environment import Environment

# 在Role类定义前添加logger配置
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class RoleReactMode(str, Enum):
    REACT = "react"
    BY_ORDER = "by_order"
    PLAN_AND_ACT = "plan_and_act"


class RoleContext(BaseModel):
    msg_buffer: list[Message] = Field(
        default_factory=list, description="消息缓冲区")
    state: int = Field(default=-1)
    todo: Optional[Action] = Field(default=None)
    actions: list[Action] = Field(
        default_factory=list, description="动作列表")  # 新增actions字段


class Role(BaseModel):
    # 添加模型配置，允许任意类型
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(default="")
    profile: str = Field(default="")
    goal: str = Field(default="")
    constraints: str = Field(default="")
    rc: RoleContext = Field(default_factory=RoleContext)
    # 修改类型注解，使用字符串形式的前向引用
    environment: Optional["Environment"] = Field(
        default=None, exclude=True)  # 新增环境字段
    # 添加任务依赖管理
    dependencies: List[str] = Field(
        default_factory=list, description="依赖的其他角色")
    memory: Dict[str, Any] = Field(default_factory=dict, description="角色记忆")

    @lru_cache(maxsize=32)
    def get_plan(self, task_description: str) -> List[Action]:
        """生成任务计划（添加缓存以复用相似任务的计划）"""
        # 实际项目中可以调用LLM生成计划
        # 这里简化为返回预设的动作列表
        return self.rc.actions

    # @property
    # def name(self) -> str:
    #     return self._name

    # @name.setter
    # def name(self, value: str):
    #     self._name = value

    def _observe(self, message: str):
        """消息接收"""
        msg = Message(context=message)
        self.rc.msg_buffer.append(msg)
        logger.debug(f"{self.name} receive message: {message}")

    # 添加反应模式属性
    react_mode: RoleReactMode = Field(default=RoleReactMode.BY_ORDER)

    async def _think(self) -> bool:
        """增强决策逻辑，支持多种反应模式"""
        if not self.rc.actions:
            return False

        if self.react_mode == RoleReactMode.REACT:
            # 基于最新消息内容进行决策
            if self.rc.msg_buffer and len(self.rc.msg_buffer) > 0:
                latest_msg = self.rc.msg_buffer[-1]
                # 这里可以添加基于消息内容的动作选择逻辑
                # 例如使用LLM分析消息并选择合适的动作
                pass
        elif self.react_mode == RoleReactMode.PLAN_AND_ACT:
            # 如果没有计划，先生成计划
            if not hasattr(self, '_plan') or not self._plan:
                task = self._extract_task_from_messages()
                self._plan = self.get_plan(task)
                self.rc.actions = self._plan
        # 默认按顺序执行动作
        if self.rc.state < len(self.rc.actions) - 1:
            self.rc.state += 1
            self.rc.todo = self.rc.actions[self.rc.state]
            return True
        # # 检查是否有新消息需要处理
        # if self.rc.msg_buffer and len(self.rc.msg_buffer) > 0:
        #     latest_msg = self.rc.msg_buffer[-1]
        #     # 根据消息内容决定下一步动作
        #     # 这里可以添加更复杂的决策逻辑

        # # 原有的顺序执行逻辑
        # if self.rc.state < len(self.rc.actions) - 1:
        #     self.rc.state += 1
        #     self.rc.todo = self.rc.actions[self.rc.state]
        #     return True
        return False

    def _extract_task_from_messages(self) -> str:
        """从消息中提取任务描述"""
        if not self.rc.msg_buffer:
            return ""
        # 简单实现：使用最新消息作为任务描述
        return self.rc.msg_buffer[-1].context

    def set_actions(self, actions: List[Action]):
        """设置角色可执行的动作列表"""
        self.rc.actions = actions
        self.rc.state = -1  # 重置状态

    async def _act(self) -> str:
        """动作执行"""
        if not self.rc.todo:
            return ""

        try:
            result = await self.rc.todo.run()
            # 新增环境消息发布逻辑
            if self.environment:
                await self.environment.publish(
                    Message(
                        context=result,
                        sent_from=self.name,
                        cause_by=self.rc.todo.__class__.__name__
                    )
                )
            return f"{self.name} executed: {result}"
        except Exception as e:
            logger.error(f"Action failed: {str(e)}")
            return f"Action error: {str(e)}"

    async def run(self, with_message: str):
        self._observe(with_message)
        await self._think()
        return await self._act()

    async def handle_message(self, message: Message) -> None:
        """处理订阅的消息"""
        self._observe(message.context)
        await self._think()
        await self._act()
