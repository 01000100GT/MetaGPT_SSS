import asyncio
import logging
from src.multiagent.actions.llm_chat_action import LLMChatAction
from src.multiagent.llm_configs.llm_config import LLMConfig, LLMType

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    # 创建LLM配置
    # llm_config = LLMConfig(
    #     api_type=LLMType.OPENAI_API_COMPATIBLE,
    #     base_url="http://localhost:8000/v1",  # 本地LLM服务地址
    #     model="gpt-3.5-turbo",  # 模型名称
    #     temperature=0.7
    # ) 

    # 创建LLM聊天动作
    chat_action = LLMChatAction(
        llm_config=None,
        system_prompt="你是一个友好的AI助手，请用简洁的语言回答问题。"
    )

    print("=== 本地LLM聊天演示 ===")
    print("输入'退出'结束对话")

    # 简单的交互循环
    while True:
        user_input = input("\n用户: ")
        if user_input.lower() in ["退出", "exit", "quit"]:
            print("\nAI: 再见！")
            break

        # 处理用户输入
        response = await chat_action.run(user_input)
        print(f"\nAI: {response}")

if __name__ == "__main__":
    asyncio.run(main())
