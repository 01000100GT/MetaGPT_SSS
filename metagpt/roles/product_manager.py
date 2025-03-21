#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/5/11 14:43
@Author  : alexanderwu
@File    : product_manager.py
@Modified By: mashenquan, 2023/11/27. Add `PrepareDocuments` action according to Section 2.2.3.5.1 of RFC 135.
"""


from metagpt.actions import UserRequirement, WritePRD
from metagpt.actions.prepare_documents import PrepareDocuments
from metagpt.roles.role import Role, RoleReactMode
from metagpt.utils.common import any_to_name


class ProductManager(Role):
    """
    代表负责产品开发和管理的产品经理角色。

    属性：
        name (str): 产品经理的名字。
        profile (str): 角色简介，默认为"产品经理"。
        goal (str): 产品经理的目标。
        constraints (str): 产品经理的约束或限制。
    """

    name: str = "Alice"
    profile: str = "Product Manager"
    goal: str = "efficiently create a successful product that meets market demands and user expectations"
    constraints: str = "utilize the same language as the user requirements for seamless communication"
    todo_action: str = ""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # 设置一个动作的角色，并设置其动作和观察模式。
        # 两个参数：1. PrepareDocuments用于准备文档和大纲
        # 2. WritePRD用于编写产品需求文档(Product Requirements Document)，PRD是详细描述产品功能、特性和目标的技术文档
        self.set_actions([PrepareDocuments, WritePRD]) 
        # 设置角色需要观察的动作类型
        # UserRequirement: 用于接收和处理用户需求
        # PrepareDocuments: 用于准备相关文档
        # 观察是否与当前角色相关
        self._watch([UserRequirement, PrepareDocuments])
        self.rc.react_mode = RoleReactMode.BY_ORDER
        self.todo_action = any_to_name(WritePRD)

    async def _observe(self, ignore_memory=False) -> int:
        return await super()._observe(ignore_memory=True)
