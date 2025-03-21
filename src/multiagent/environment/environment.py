from typing import Dict, Set, Coroutine, Any, Callable, Awaitable, List, TYPE_CHECKING
from src.multiagent.schema.message import Message
# 使用TYPE_CHECKING条件导入
if TYPE_CHECKING:
    from src.multiagent.roles.role import Role
import asyncio
import logging

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class Environment:
    """
    多Agent交互环境
    单例模式
    """

    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            # 移除对__init__的显式调用
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # 防止重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return

        # 修正类型注解，使用Awaitable更符合Python 3.10规范
        self._subscriptions: Dict[str,
                                  Set[Callable[[Message], Awaitable[None]]]] = {}
        self._message_queue = asyncio.Queue(maxsize=1000)  # 限制队列大小
        self._message_history: List[Message] = []  # 添加消息历史
        self._initialized = True
        logger.debug("环境初始化完成")

    async def broadcast(self, message: Message):
        """向所有角色广播消息"""
        await self.publish(message)

    def get_history(self, limit: int | None = -1, filter_by: str | None = None) -> List[Message]:
        """获取消息历史

        Args:
            limit: 限制返回的消息数量
            filter_by: 按发送者或cause_by筛选

        Returns:
            List[Message]: 消息历史列表
        """
        history = self._message_history

        if filter_by:
            history = [msg for msg in history if
                       msg.sent_from == filter_by or msg.cause_by == filter_by]

        if limit and limit > 0:
            history = history[-limit:]

        return history

    async def add_role(self, role: 'Role', subscriptions: List[str] = []):
        """添加角色到环境并设置订阅

        Args:
            role: 要添加的角色
            subscriptions: 要订阅的消息类型列表
        """
        # 设置角色的环境引用
        role.environment = self

        # 设置订阅
        if subscriptions:
            for topic in subscriptions:
                await self.subscribe(topic, role.handle_message)

    async def publish(self, message: Message):
        """发布消息到环境"""
        # 记录消息历史
        self._message_history.append(message)
        # 限制历史大小
        if len(self._message_history) > 100:
            self._message_history = self._message_history[-100:]

        await self._message_queue.put(message)
        logger.debug(f"消息已发布: {message.sent_from} -> {message.cause_by}")

    async def subscribe(self, topic: str, callback: Callable[[Message], Awaitable[None]]):
        """订阅环境消息"""
        if topic not in self._subscriptions:
            self._subscriptions[topic] = set()
        self._subscriptions[topic].add(callback)
        logger.debug(f"已添加订阅: {topic}")

    def unsubscribe(self, topic: str, callback: Callable[[Message], Awaitable[None]]):
        """取消订阅环境消息"""
        if topic in self._subscriptions and callback in self._subscriptions[topic]:
            self._subscriptions[topic].remove(callback)
            logger.debug(f"已移除订阅: {topic}")

    async def run(self):
        """启动环境消息分发"""
        while True:
            try:
                # 获取消息并添加超时保护
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=60.0
                )

                # 匹配订阅者
                matched_subscribers = set()

                # 1. 精确匹配
                if message.cause_by in self._subscriptions:
                    matched_subscribers.update(
                        self._subscriptions[message.cause_by])

                # 2. 通配符匹配
                if "*" in self._subscriptions:
                    matched_subscribers.update(self._subscriptions["*"])

                # 执行回调
                if matched_subscribers:
                    await asyncio.gather(
                        *[callback(message) for callback in matched_subscribers]
                    )

                # 标记任务完成
                self._message_queue.task_done()

            except asyncio.TimeoutError:
                # 超时继续循环
                continue
            except Exception as e:
                logger.error(f"消息处理异常: {e}", exc_info=True)
                # 确保队列任务完成
                self._message_queue.task_done()
