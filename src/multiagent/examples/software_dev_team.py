import asyncio
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING

# 将相对导入改为绝对导入
from src.multiagent.actions.action import Action
from src.multiagent.actions.llm_chat_action import LLMChatAction
from src.multiagent.environment.environment import Environment
# if TYPE_CHECKING: 条件语句后添加了 else: 分支，在非类型检查时导入 Role 类。这样可以避免循环导入问题，同时确保在运行时能够正确引用 Role 类。
# 避免循环导入问题
if TYPE_CHECKING:
    from src.multiagent.roles.role import Role
else:
    # 在非类型检查时导入Role类
    from src.multiagent.roles.role import Role
from src.multiagent.schema.message import Message, MessageType
from src.multiagent.tasks.task import Task
from src.multiagent.tools.tool_registry import tool_registry
from src.multiagent.workflow.workflow_manager import workflow_manager

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class WritePRD(LLMChatAction):
    """PRD编写动作"""
    name: str = "WritePRD"
    desc: str = "编写产品需求文档"

    def __init__(self):
        super().__init__()
        # 使用类型注解，更清晰地表明role属性的类型
        self.role: Optional['Role'] = None
    # PRD模板
    prompt_template: str = """
    你是一名专业的产品经理。请根据以下需求编写一份详细的产品需求文档(PRD)：

    需求: {input}

    PRD应包含以下部分：
    1. 产品概述
    2. 目标用户
    3. 用户故事
    4. 功能需求（详细描述每个功能点）
    5. 非功能需求（性能、安全等）
    6. 验收标准

    请确保PRD内容清晰、结构化，并使用markdown格式。
    """

    async def run(self, input_text: str = "", **kwargs) -> str:
        """执行PRD编写动作"""
        logger.info(f"开始编写PRD，需求: {input_text}")

        # 调用LLM生成PRD
        prd_content = await super().run(input_text, **kwargs)

        # 发布PRD完成消息
        if self.role and self.role.environment:
            message = Message(
                context=prd_content,
                type=MessageType.RESULT,
                sent_from=self.role.name,
                cause_by=self.name
            )
            # 将同步调用改为异步任务
            asyncio.create_task(self.role.environment.publish(message))

        return prd_content


class WriteDesign(LLMChatAction):
    """系统设计动作"""
    name: str = "WriteDesign"
    desc: str = "编写系统设计文档"

    def __init__(self):
        super().__init__()
        # 使用类型注解，更清晰地表明role属性的类型
        self.role: Optional['Role'] = None
    # 设计模板
    prompt_template: str = """
    你是一名专业的软件架构师。请根据以下PRD编写一份详细的系统设计文档：

    PRD内容:
    {input}

    设计文档应包含以下部分：
    1. 系统架构概述
    2. 组件设计
    3. 数据模型
    4. API设计
    5. 技术选型
    6. 部署架构

    请确保设计文档内容清晰、结构化，并使用markdown格式。
    """

    async def run(self, input_text: str = "", **kwargs) -> str:
        """执行系统设计动作"""
        # 获取PRD内容
        prd_content = input_text
        if not prd_content and self.role and self.role.rc.msg_buffer:
            for msg in self.role.rc.msg_buffer:
                if msg.cause_by == "WritePRD":
                    prd_content = msg.context
                    break

        if not prd_content:
            logger.warning("未找到PRD内容，无法进行系统设计")
            return "错误：未找到PRD内容"

        logger.info("开始编写系统设计")

        # 调用LLM生成设计文档
        design_content = await super().run(prd_content, **kwargs)

        # 发布设计完成消息
        if self.role and self.role.environment:
            message = Message(
                context=design_content,
                type=MessageType.RESULT,
                sent_from=self.role.name,
                cause_by=self.name
            )
            # 将同步调用改为异步任务
            asyncio.create_task(self.role.environment.publish(message))
        return design_content


class WriteCode(LLMChatAction):
    """代码编写动作"""
    name: str = "WriteCode"
    desc: str = "编写代码实现"

    def __init__(self):
        super().__init__()
        # 使用类型注解，更清晰地表明role属性的类型
        self.role: Optional['Role'] = None
    # 代码生成模板
    prompt_template: str = """
    你是一名专业的软件工程师。请根据以下系统设计编写实现代码：
    
    系统设计:
    {input}
    
    请提供完整的代码实现，包括：
    1. 项目结构
    2. 核心类和函数
    3. 必要的注释
    
    代码应当遵循良好的编程实践，包括清晰的命名、适当的注释和错误处理。
    """

    async def run(self, input_text: str = "", **kwargs) -> str:
        """执行代码编写动作"""
        # 获取设计文档内容
        design_content = input_text
        if not design_content and self.role and self.role.rc.msg_buffer:
            for msg in self.role.rc.msg_buffer:
                if msg.cause_by == "WriteDesign":
                    design_content = msg.context
                    break

        if not design_content:
            logger.warning("未找到设计文档内容，无法进行代码编写")
            return "错误：未找到设计文档内容"

        logger.info("开始编写代码")

        # 调用LLM生成代码
        code_content = await super().run(design_content, **kwargs)

        # 发布代码完成消息
        if self.role and self.role.environment:
            await self.role.environment.publish(Message(
                context=code_content,
                type=MessageType.RESULT,
                sent_from=self.role.name,
                cause_by=self.name
            ))

        return code_content


class WriteTest(LLMChatAction):
    """测试编写动作"""
    name: str = "WriteTest"
    desc: str = "编写测试用例"

    def __init__(self):
        super().__init__()
        # 使用类型注解，更清晰地表明role属性的类型
        self.role: Optional['Role'] = None
    # 测试用例模板
    prompt_template: str = """
    你是一名专业的QA工程师。请根据以下代码实现编写测试用例：
    
    代码实现:
    {input}
    
    请提供完整的测试用例，包括：
    1. 单元测试
    2. 集成测试
    3. 边界条件测试
    4. 异常情况测试
    
    测试用例应当全面覆盖功能点，确保代码质量。
    """

    async def run(self, input_text: str = "", **kwargs) -> str:
        """执行测试用例编写动作"""
        # 获取代码内容
        code_content = input_text
        if not code_content and self.role and self.role.rc.msg_buffer:
            for msg in self.role.rc.msg_buffer:
                if msg.cause_by == "WriteCode":
                    code_content = msg.context
                    break

        if not code_content:
            logger.warning("未找到代码内容，无法编写测试用例")
            return "错误：未找到代码内容"

        logger.info("开始编写测试用例")

        # 调用LLM生成测试用例
        test_content = await super().run(code_content, **kwargs)

        # 发布测试完成消息
        if self.role and self.role.environment:
            await self.role.environment.publish(Message(
                context=test_content,
                type=MessageType.RESULT,
                sent_from=self.role.name,
                cause_by=self.name
            ))

        return test_content


class ProductManager(Role):
    """产品经理角色"""

    def __init__(self, name: str = "ProductManager"):
        super().__init__(name=name)
        action = WritePRD()
        action.role = self  # 设置role属性
        self.set_actions([action])

    async def _think(self) -> bool:
        """思考下一步行动"""
        # 简化版：直接选择WritePRD动作
        if self.rc.msg_buffer and len(self.rc.msg_buffer) > 0:
            self.rc.todo = self.rc.actions[0]
            return True
        return False


class Architect(Role):
    """架构师角色"""

    def __init__(self, name: str = "Architect"):
        super().__init__()  # 默认初始化
        self.name = name
        action = WriteDesign()
        action.role = self  # 设置role属性
        self.set_actions([action])

    async def _think(self) -> bool:
        """思考下一步行动"""
        # 检查是否有PRD完成的消息
        for msg in self.rc.msg_buffer:
            if msg.cause_by == "WritePRD":
                self.rc.todo = self.rc.actions[0]
                return True
        return False


class Engineer(Role):
    """工程师角色"""

    def __init__(self, name: str = "Engineer"):
        super().__init__()  # 默认初始化
        self.name = name
        action = WriteCode()
        action.role = self  # 设置role属性
        self.set_actions([action])

    async def _think(self) -> bool:
        """思考下一步行动"""
        # 检查是否有设计完成的消息
        for msg in self.rc.msg_buffer:
            if msg.cause_by == "WriteDesign":
                self.rc.todo = self.rc.actions[0]
                return True
        return False


class QAEngineer(Role):
    """QA工程师角色"""

    def __init__(self, name: str = "QAEngineer"):
        super().__init__()  # 默认初始化
        self.name = name
        action = WriteTest()
        action.role = self  # 设置role属性
        self.set_actions([action])

    async def _think(self) -> bool:
        """思考下一步行动"""
        # 检查是否有代码完成的消息
        for msg in self.rc.msg_buffer:
            if msg.cause_by == "WriteCode":
                self.rc.todo = self.rc.actions[0]
                return True
        return False


class SoftwareDevTeam:
    """软件开发团队"""

    def __init__(self):
        # 创建环境
        self.environment = Environment()

        # 创建角色
        self.product_manager = ProductManager()
        self.architect = Architect()
        self.engineer = Engineer()
        self.qa_engineer = QAEngineer()

        # 设置角色环境
        self.product_manager.environment = self.environment
        self.architect.environment = self.environment
        self.engineer.environment = self.environment
        self.qa_engineer.environment = self.environment

        # 设置订阅关系
        # 在初始化时调用异步函数需要使用事件循环
        asyncio.create_task(self._setup_subscriptions())

    async def _setup_subscriptions(self):
        """设置消息订阅"""
        # 产品经理接收用户需求
        await self.environment.subscribe("user_requirement", self.product_manager.handle_message)

        # 架构师接收PRD
        await self.environment.subscribe("WritePRD", self.architect.handle_message)

        # 工程师接收设计文档
        await self.environment.subscribe("WriteDesign", self.engineer.handle_message)

        # QA工程师接收代码
        await self.environment.subscribe("WriteCode", self.qa_engineer.handle_message)

    async def start_project(self, requirement: str):
        """启动项目开发"""
        logger.info(f"开始项目: {requirement}")

        # 发布用户需求
        await self.environment.publish(Message(
            context=requirement,
            type=MessageType.TEXT,
            sent_from="user",
            cause_by="user_requirement"
        ))

        # 启动环境消息处理
        env_task = asyncio.create_task(self.environment.run())

        # 启动各角色，为每个角色提供初始消息
        pm_task = asyncio.create_task(
            self.product_manager.run(with_message=requirement))
        arch_task = asyncio.create_task(
            self.architect.run(with_message="等待PRD完成"))
        eng_task = asyncio.create_task(
            self.engineer.run(with_message="等待系统设计完成"))
        qa_task = asyncio.create_task(
            self.qa_engineer.run(with_message="等待代码实现完成"))

        # 等待所有任务完成
        await asyncio.gather(pm_task, arch_task, eng_task, qa_task)

        # 取消环境任务
        env_task.cancel()

        logger.info("项目开发完成")

    async def start_project_workflow(self, requirement: str):
        """使用工作流管理器启动项目"""
        # 创建工作流
        workflow = workflow_manager.create_workflow(
            name=f"Project_{requirement[:20]}",
            description=f"开发项目: {requirement}"
        )

        # 创建任务
        prd_task = Task(
            description="编写PRD",
            agent=self.product_manager,
            dependencies=[]
        )

        design_task = Task(
            description="系统设计",
            agent=self.architect,
            dependencies=[]
        )

        code_task = Task(
            description="代码实现",
            agent=self.engineer,
            dependencies=[]
        )

        test_task = Task(
            description="测试用例",
            agent=self.qa_engineer,
            dependencies=[]
        )

        # 添加任务到工作流
        workflow_manager.add_task_to_workflow(workflow.name, prd_task)
        workflow_manager.add_task_to_workflow(workflow.name, design_task)
        workflow_manager.add_task_to_workflow(workflow.name, code_task)
        workflow_manager.add_task_to_workflow(workflow.name, test_task)

        # 设置依赖关系
        workflow_manager.set_task_dependencies(
            workflow.name, "系统设计", ["编写PRD"])
        workflow_manager.set_task_dependencies(
            workflow.name, "代码实现", ["系统设计"])
        workflow_manager.set_task_dependencies(
            workflow.name, "测试用例", ["代码实现"])

        # 执行工作流
        context = {"requirement": requirement}
        results = await workflow_manager.execute_workflow(workflow.name, context)

        logger.info("项目开发完成")
        return results


# 使用示例
async def main():
    """主函数"""
    # 创建软件开发团队
    team = SoftwareDevTeam()

    # 启动项目
    requirement = "开发一个2048游戏，具有基本的游戏功能和分数记录功能"

    # 方法1: 使用基本流程
    # await team.start_project(requirement)

    # 方法2: 使用工作流管理器
    results = await team.start_project_workflow(requirement)

    # 打印结果
    print("\n" + "="*50)
    print(f"软件开发项目完成: {requirement}")
    print("="*50)

    for task_name, result in results.items():
        print(f"\n--- {task_name} ---")
        # 只打印前300个字符，避免输出过长
        print(f"{result[:300]}..." if len(result) > 300 else result)

    return results


# 如果直接运行此脚本
if __name__ == "__main__":
    import asyncio

    # 设置日志级别
    logging.basicConfig(level=logging.INFO)

    # 运行主函数
    results = asyncio.run(main())
