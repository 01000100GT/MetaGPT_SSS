import asyncio
import logging
from typing import List, Optional
from pydantic import Field

from src.multiagent.environment.environment import Environment
from src.multiagent.roles.role import Role
from src.multiagent.schema.message import Message, MessageType
from src.multiagent.actions.llm_chat_action import LLMChatAction

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ChatAction(LLMChatAction):
    """聊天动作"""
    name: str = "Chat"
    desc: str = "与用户进行对话"
    # 添加role字段声明
    role: Optional[Role] = Field(default=None, description="关联的角色")

    def __init__(self):
        super().__init__()

    # 聊天模板
    prompt_template: str = """
    你是一个友好的AI助手。请根据用户的消息进行回复：

    用户消息: {input}

    请提供有帮助、友好且信息丰富的回答。
    """

    async def run(self, input_text: str = "", **kwargs) -> str:
        """执行聊天动作"""
        logger.info(f"收到用户消息: {input_text}")

        # 调用LLM生成回复
        reply = await super().run(input_text, **kwargs)

        # 发布回复消息
        if self.role and self.role.environment:
            message = Message(
                context=reply,
                type=MessageType.TEXT,
                sent_from=self.role.name,
                cause_by=self.name
            )
            # 使用异步任务发布消息
            asyncio.create_task(self.role.environment.publish(message))

        return reply


class Assistant(Role):
    """AI助手角色"""

    def __init__(self, name: str = "AI助手"):
        super().__init__(name=name)
        action = ChatAction()
        action.role = self
        self.set_actions([action])

    async def _think(self) -> bool:
        """思考下一步行动"""
        # 检查是否有新消息
        if self.rc.msg_buffer and len(self.rc.msg_buffer) > 0:
            self.rc.todo = self.rc.actions[0]
            return True
        return False


class SimpleChat:
    """简单聊天系统"""

    def __init__(self):
        # 创建环境
        self.environment = Environment()

        # 创建AI助手
        self.assistant = Assistant()

        # 设置环境
        self.assistant.environment = self.environment

        # 设置订阅关系
        asyncio.create_task(self._setup_subscriptions())

    async def _setup_subscriptions(self):
        """设置消息订阅"""
        # AI助手接收用户消息
        await self.environment.subscribe("user_message", self.assistant.handle_message)

    async def start(self):
        """启动聊天系统"""
        print("\n=== 简单聊天系统启动 ===")
        print("输入'退出'结束聊天")

        # 创建消息队列用于存储AI助手的回复
        assistant_replies = []

        # 定义消息处理回调函数
        async def message_handler(message: Message):
            if message.sent_from == self.assistant.name:
                assistant_replies.append(message)
                # 添加日志，帮助调试
                logger.debug(f"收到AI助手回复: {message.context[:50]}...")

        # 订阅AI助手的消息
        await self.environment.subscribe(self.assistant.name, message_handler)

        # 启动环境消息处理
        env_task = asyncio.create_task(self.environment.run())

        # 启动AI助手并等待初始消息处理完成
        initial_message = "你好，我是AI助手，有什么可以帮助你的？"
        await self.assistant.run(with_message=initial_message)
        # 等待初始消息显示
        await asyncio.sleep(1)

        try:
            # 主聊天循环
            while True:
                # 显示AI助手的回复
                if assistant_replies:
                    for msg in assistant_replies:
                        print(f"\nAI助手: {msg.context}")
                    assistant_replies.clear()

                # 获取用户输入
                user_input = input("\n用户: ")

                # 检查退出条件
                if user_input.lower() in ['/退出', '/exit', '/Exit', '/quit', '/Quit', '/bye', '/Bye', '/goodbye', '/Goodbye']:
                    break

                # 发布用户消息
                await self.environment.publish(Message(
                    context=user_input,
                    type=MessageType.TEXT,
                    sent_from="用户",
                    cause_by="user_message"
                ))

                # 等待AI助手处理 - 使用更智能的等待机制
                wait_count = 0
                max_wait = 20  # 最多等待10秒
                while wait_count < max_wait and not assistant_replies:
                    await asyncio.sleep(1.5)
                    wait_count += 1

                # 如果等待超时，提示用户
                if wait_count >= max_wait and not assistant_replies:
                    print("\nAI助手: [似乎没有收到回复，可能需要检查LLM连接]")

        except KeyboardInterrupt:
            print("\n聊天已中断")
        finally:
            # 取消任务
            env_task.cancel()
            # assistant_task.cancel()
            print("\n=== 聊天系统已关闭 ===")


# 测试代码
if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)

    # 运行聊天系统
    asyncio.run(SimpleChat().start())
