from typing import Dict, Callable, Any, Set
import inspect
import logging
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

class ToolCategory(str, Enum):
    """工具分类"""
    GENERAL = "general"  # 通用工具
    DATA = "data"        # 数据处理
    WEB = "web"          # 网络工具
    FILE = "file"        # 文件操作
    API = "api"          # API调用
    CUSTOM = "custom"    # 自定义类别


class ToolRegistry:
    """工具注册中心"""
    _instance = None

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self.tools: Dict[str, Callable] = {}
        self.categories: Dict[str, Set[str]] = {
            cat.value: set() for cat in ToolCategory}
        self.usage_stats: Dict[str, int] = {}  # 工具使用统计
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}  # 工具元数据
        self._initialized = True

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # cls._instance.__init__()  # 显式调用初始化
        return cls._instance

    def register(self, name: str, tool_func: Callable,
                 category: str = ToolCategory.GENERAL.value,
                 description: str | None = None,
                 required_roles: Set[str] | None = None) -> None:
        """注册工具

        Args:
            name: 工具名称
            tool_func: 工具函数
            category: 工具分类
            description: 工具描述
            required_roles: 允许使用此工具的角色集合
        """
        # 验证工具函数是否有类型注解
        sig = inspect.signature(tool_func)
        missing_annotations = []
        for param_name, param in sig.parameters.items():
            if param.annotation == inspect.Parameter.empty:
                missing_annotations.append(param_name)
                logger.warning(f"工具函数 {name} 的参数 {param_name} 缺少类型注解")

        if sig.return_annotation == inspect.Signature.empty:
            logger.warning(f"工具函数 {name} 缺少返回值类型注解")

        # 检查分类是否有效
        if category not in [cat.value for cat in ToolCategory]:
            logger.warning(f"无效的工具分类 '{category}'，使用默认分类 'general'")
            category = ToolCategory.GENERAL.value

        # 注册工具
        self.tools[name] = tool_func
        self.categories[category].add(name)
        self.usage_stats[name] = 0

        # 存储元数据
        self.tool_metadata[name] = {
            "description": description or inspect.getdoc(tool_func) or "无描述",
            "category": category,
            "is_async": asyncio.iscoroutinefunction(tool_func),
            "required_roles": required_roles or set(),
            "missing_annotations": missing_annotations,
            "signature": str(sig)
        }

        logger.info(f"工具 {name} 已注册")

    async def execute(self, name: str, role_name: str | None = None, *args, **kwargs) -> Any:
        """执行工具函数

        Args:
            name: 工具名称
            role_name: 调用者角色名称，用于权限检查
            *args, **kwargs: 传递给工具函数的参数

        Returns:
            工具函数执行结果
        """
        if name not in self.tools:
            raise ValueError(f"未找到工具: {name}")

        # 权限检查
        required_roles = self.tool_metadata[name].get("required_roles")
        if required_roles and role_name and role_name not in required_roles:
            raise PermissionError(f"角色 {role_name} 没有权限使用工具 {name}")

        # 更新使用统计
        self.usage_stats[name] += 1

        # 执行工具函数
        tool_func = self.tools[name]
        if self.tool_metadata[name]["is_async"]:
            return await tool_func(*args, **kwargs)
        else:
            return tool_func(*args, **kwargs)

    def get_tool(self, name: str) -> Callable:
        """获取工具函数"""
        if name not in self.tools:
            raise ValueError(f"未找到工具: {name}")
        return self.tools[name]

    def list_tools(self, category: str | None = None, role_name: str | None = None) -> Dict[str, str]:
        """列出所有可用工具及其描述

        Args:
            category: 按分类筛选
            role_name: 按角色权限筛选

        Returns:
            Dict[str, str]: 工具名称到描述的映射
        """
        result = {}

        for name, func in self.tools.items():
            # 按分类筛选
            if category and self.tool_metadata[name]["category"] != category:
                continue

            # 按角色权限筛选
            required_roles = self.tool_metadata[name].get("required_roles")
            if required_roles and role_name and role_name not in required_roles:
                continue

            result[name] = self.tool_metadata[name]["description"]

        return result


# 全局工具注册表实例
tool_registry = ToolRegistry()
# tool_registry.register("get_current_time", lambda: f"当前时间为: {inspect.getdoc(inspect.currentframe())}")
