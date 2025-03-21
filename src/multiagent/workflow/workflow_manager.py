from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from pydantic import BaseModel, Field
import asyncio
import logging
from enum import Enum
from datetime import datetime

from src.multiagent.roles.role import Role
from src.multiagent.tasks.task import Task
from src.multiagent.schema.message import Message, MessageType
from src.multiagent.environment.environment import Environment

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class WorkflowStatus(str, Enum):
    """工作流状态枚举"""
    PENDING = "pending"     # 等待执行
    RUNNING = "running"     # 正在执行
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"       # 执行失败
    PAUSED = "paused"       # 已暂停


class Workflow(BaseModel):
    """工作流定义"""
    name: str
    description: str = ""
    tasks: List[Task] = Field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    result: Optional[Any] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_task(self, task: Task) -> None:
        """添加任务"""
        self.tasks.append(task)
        self.updated_at = datetime.now()

    def get_task_by_description(self, description: str) -> Optional[Task]:
        """根据描述获取任务"""
        for task in self.tasks:
            if task.description == description:
                return task
        return None

    def set_dependencies(self, task: Task, dependencies: List[str]) -> None:
        """设置任务依赖关系"""
        for dep_desc in dependencies:
            dep_task = self.get_task_by_description(dep_desc)
            if dep_task:
                task.dependencies.append(dep_task)
            else:
                logger.warning(f"依赖任务 '{dep_desc}' 不存在")
        self.updated_at = datetime.now()


class WorkflowManager:
    """工作流管理器"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return

        self.workflows: Dict[str, Workflow] = {}
        self.active_workflow: Optional[str] = None
        self.environment = Environment()
        self._initialized = True

    def create_workflow(self, name: str, description: str = "") -> Workflow:
        """创建工作流"""
        if name in self.workflows:
            logger.warning(f"工作流 '{name}' 已存在，将被覆盖")

        workflow = Workflow(name=name, description=description)
        self.workflows[name] = workflow
        return workflow

    def get_workflow(self, name: str) -> Optional[Workflow]:
        """获取工作流"""
        return self.workflows.get(name)

    def set_active_workflow(self, name: str) -> bool:
        """设置活动工作流"""
        if name not in self.workflows:
            logger.error(f"工作流 '{name}' 不存在")
            return False

        self.active_workflow = name
        return True

    def add_task_to_workflow(self, workflow_name: str, task: Task) -> bool:
        """向工作流添加任务"""
        workflow = self.get_workflow(workflow_name)
        if not workflow:
            logger.error(f"工作流 '{workflow_name}' 不存在")
            return False

        workflow.add_task(task)
        return True

    def set_task_dependencies(self, workflow_name: str, task_desc: str, dependencies: List[str]) -> bool:
        """设置任务依赖关系"""
        workflow = self.get_workflow(workflow_name)
        if not workflow:
            logger.error(f"工作流 '{workflow_name}' 不存在")
            return False

        task = workflow.get_task_by_description(task_desc)
        if not task:
            logger.error(f"任务 '{task_desc}' 不存在")
            return False

        workflow.set_dependencies(task, dependencies)
        return True

    async def execute_workflow(self, name: str, context: Dict[str, Any] | None = None) -> Any:
        """执行工作流"""
        workflow = self.get_workflow(name)
        if not workflow:
            raise ValueError(f"工作流 '{name}' 不存在")

        # 设置为活动工作流
        self.active_workflow = name

        # 更新状态
        workflow.status = WorkflowStatus.RUNNING
        workflow.updated_at = datetime.now()

        try:
            # 构建任务执行顺序（拓扑排序）
            execution_order = self._build_execution_order(workflow)

            # 执行任务
            results = {}
            ctx = context or {}

            for task in execution_order:
                logger.info(f"执行任务: {task.description}")

                # 发布任务开始消息
                await self.environment.publish(Message(
                    context=f"开始执行任务: {task.description}",
                    type=MessageType.SYSTEM,
                    cause_by="workflow_manager"
                ))

                # 执行任务
                try:
                    result = await task.execute(ctx)
                    results[task.description] = result

                    # 更新上下文
                    ctx[task.description] = result

                    # 发布任务完成消息
                    await self.environment.publish(Message(
                        context=result,
                        type=MessageType.RESULT,
                        cause_by=task.description
                    ))

                except Exception as e:
                    logger.error(f"任务 '{task.description}' 执行失败: {str(e)}")

                    # 发布任务失败消息
                    await self.environment.publish(Message(
                        context=str(e),
                        type=MessageType.ERROR,
                        cause_by=task.description
                    ))

                    # 更新工作流状态
                    workflow.status = WorkflowStatus.FAILED
                    workflow.updated_at = datetime.now()

                    raise

            # 更新工作流状态和结果
            workflow.status = WorkflowStatus.COMPLETED
            workflow.result = results
            workflow.updated_at = datetime.now()

            return results

        except Exception as e:
            logger.error(f"工作流 '{name}' 执行失败: {str(e)}")

            # 确保状态更新为失败
            workflow.status = WorkflowStatus.FAILED
            workflow.updated_at = datetime.now()

            raise

    def _build_execution_order(self, workflow: Workflow) -> List[Task]:
        """构建任务执行顺序（拓扑排序）"""
        # 初始化
        result = []
        visited = set()
        temp_visited = set()

        # 定义DFS函数
        def dfs(task: Task):
            # 检测循环依赖
            if task in temp_visited:
                raise ValueError(f"检测到循环依赖: {task.description}")

            # 跳过已访问的任务
            if task in visited:
                return

            # 标记为临时访问
            temp_visited.add(task)

            # 递归访问依赖任务
            for dep in task.dependencies:
                dfs(dep)

            # 标记为已访问
            temp_visited.remove(task)
            visited.add(task)

            # 添加到结果
            result.append(task)

        # 对所有任务执行DFS
        for task in workflow.tasks:
            if task not in visited:
                dfs(task)

        return result

    def pause_workflow(self, name: str) -> bool:
        """暂停工作流"""
        workflow = self.get_workflow(name)
        if not workflow:
            logger.error(f"工作流 '{name}' 不存在")
            return False

        if workflow.status != WorkflowStatus.RUNNING:
            logger.warning(f"工作流 '{name}' 不在运行状态，无法暂停")
            return False

        workflow.status = WorkflowStatus.PAUSED
        workflow.updated_at = datetime.now()
        return True

    def resume_workflow(self, name: str) -> bool:
        """恢复工作流"""
        workflow = self.get_workflow(name)
        if not workflow:
            logger.error(f"工作流 '{name}' 不存在")
            return False

        if workflow.status != WorkflowStatus.PAUSED:
            logger.warning(f"工作流 '{name}' 不在暂停状态，无法恢复")
            return False

        workflow.status = WorkflowStatus.RUNNING
        workflow.updated_at = datetime.now()

        # 异步执行剩余任务
        asyncio.create_task(self._resume_execution(workflow))
        return True

    async def _resume_execution(self, workflow: Workflow) -> None:
        """恢复执行工作流"""
        # 实际实现中需要记录执行状态，以便从中断点恢复
        # 这里简化为重新执行整个工作流
        try:
            await self.execute_workflow(workflow.name)
        except Exception as e:
            logger.error(f"恢复工作流 '{workflow.name}' 失败: {str(e)}")

    def delete_workflow(self, name: str) -> bool:
        """删除工作流"""
        if name not in self.workflows:
            logger.warning(f"工作流 '{name}' 不存在")
            return False

        if self.active_workflow == name:
            self.active_workflow = None

        del self.workflows[name]
        return True

    def list_workflows(self) -> Dict[str, Dict[str, Any]]:
        """列出所有工作流"""
        return {
            name: {
                "description": workflow.description,
                "status": workflow.status,
                "created_at": workflow.created_at.isoformat(),
                "updated_at": workflow.updated_at.isoformat(),
                "task_count": len(workflow.tasks)
            }
            for name, workflow in self.workflows.items()
        }

    def get_workflow_details(self, name: str) -> Dict[str, Any]:
        """获取工作流详情"""
        workflow = self.get_workflow(name)
        if not workflow:
            raise ValueError(f"工作流 '{name}' 不存在")

        return {
            "name": workflow.name,
            "description": workflow.description,
            "status": workflow.status,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat(),
            "tasks": [
                {
                    "description": task.description,
                    "status": task.status,
                    "dependencies": [dep.description for dep in task.dependencies]
                }
                for task in workflow.tasks
            ],
            "result": workflow.result
        }


# 全局工作流管理器实例
workflow_manager = WorkflowManager()
