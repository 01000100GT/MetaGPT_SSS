from metagpt.context import Context
from metagpt.roles.product_manager import ProductManager
from metagpt.logs import logger
import json
import re


async def main():
    msg: str = "写一个PC格斗游戏的产品需求文档"
    context = Context()  # 显示创建上下文会话对象， Role对象会隐式的自动将其共享给自己的Action对象
    # 角色类
    role = ProductManager(context=context) 
    while msg:
        result = await role.run(msg)
        msg = str(result) if result else ""
        logger.info(msg)
     