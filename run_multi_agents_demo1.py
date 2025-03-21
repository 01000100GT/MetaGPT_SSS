#!/usr/bin/env python3
"""
MetaGPT多智能体系统启动脚本
"""
from src.multiagent.examples.software_dev_team import SoftwareDevTeam
from src.multiagent.examples.simple_chat import SimpleChat
import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

# 检查配置文件


def check_config():
    """检查LLM配置文件是否存在"""
    config_path = Path.home() / ".metagpt" / "config2.yaml"
    if not config_path.exists():
        print(f"警告: 配置文件不存在: {config_path}")
        print("请创建配置文件或使用示例配置")

        # 检查示例配置
        example_config = Path(__file__).parent / \
            "config" / "config2.example.yaml"
        if example_config.exists():
            # 创建目录
            config_dir = Path.home() / ".metagpt"
            config_dir.mkdir(exist_ok=True)

            # 复制示例配置
            import shutil
            shutil.copy(example_config, config_path)
            print(f"已复制示例配置到: {config_path}")
            return True
        else:
            print(f"示例配置也不存在: {example_config}")
            return False
    return True


def setup_logging(level=logging.INFO):
    """设置日志级别"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("metagpt.log")
        ]
    )


async def run_software_dev(requirement: str):
    """运行软件开发团队示例"""
    team = SoftwareDevTeam()
    results = await team.start_project_workflow(requirement)

    # 打印结果
    print("\n" + "="*50)
    print(f"软件开发项目完成: {requirement}")
    print("="*50)

    for task_name, result in results.items():
        print(f"\n--- {task_name} ---")
        # 只打印前300个字符，避免输出过长
        print(f"{result[:300]}..." if len(result) > 300 else result)

    # 保存结果到文件
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # 创建项目目录
    project_name = requirement.split()[1] if len(
        requirement.split()) > 1 else "project"
    project_dir = output_dir / project_name
    project_dir.mkdir(exist_ok=True)

    # 保存各阶段结果
    for task_name, result in results.items():
        file_name = f"{task_name.lower().replace(' ', '_')}.md"
        with open(project_dir / file_name, "w", encoding="utf-8") as f:
            f.write(result)

    print(f"\n所有结果已保存到: {project_dir}")
    return results


async def run_simple_chat():
    """运行简单聊天示例"""
    try:
        chat = SimpleChat()
        await chat.start()
    except Exception as e:
        print(f"\n聊天系统出错: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MetaGPT多智能体系统")
    parser.add_argument("--mode", type=str, default="chat",
                        choices=["dev", "chat"],
                        help="运行模式: dev(软件开发), chat(聊天)")
    parser.add_argument("--requirement", type=str,
                        default="开发一个简单的待办事项管理应用",
                        help="软件开发需求描述")
    parser.add_argument("--debug", action="store_true",
                        help="启用调试模式")

    args = parser.parse_args()

    # 设置日志级别
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)

    # 检查配置文件
    if not check_config():
        print("配置文件检查失败，程序可能无法正常运行")

    # 根据模式运行不同示例
    if args.mode == "dev":
        await run_software_dev(args.requirement)
    elif args.mode == "chat":
        await run_simple_chat()


if __name__ == "__main__":
    asyncio.run(main())
