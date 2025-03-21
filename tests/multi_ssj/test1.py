import pytest
import asyncio
import sys
import os
# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.multiagent.environment.environment import Environment
from src.multiagent.schema.message import Message


@pytest.mark.asyncio
async def test_environment_singleton():
    """测试环境单例模式"""
    env1 = Environment()
    env2 = Environment()
    assert env1 is env2


@pytest.mark.asyncio
async def test_publish_subscribe():
    """测试发布订阅机制"""
    env = Environment()

    # 测试数据
    received_messages = []

    # 定义回调
    async def callback(message: Message):
        received_messages.append(message)

     # 订阅消息 - 使用与cause_by相同的主题
    topic = "action"  # 修改这里，与cause_by保持一致
    await env.subscribe(topic, callback)

    # 发布消息
    test_message = Message(context="测试内容", cause_by="action")
    await env.publish(test_message)

    # 启动环境处理
    task = asyncio.create_task(env.run())

    # 等待消息处理
    await asyncio.sleep(10)  # 增加等待时间，确保消息被处理

    # 验证消息接收
    assert len(received_messages) == 1
    assert received_messages[0].context == "测试内容"

    # 清理
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
