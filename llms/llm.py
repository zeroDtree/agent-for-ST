from langchain_openai import ChatOpenAI

import os


def get_llm_model(model_name: str):
    if model_name in ["deepseek-chat", "deepseek-reasoner"]:
        apikey = os.getenv("DEEPSEEK_API_KEY")
        return ChatOpenAI(
            api_key=apikey,
            base_url="https://api.deepseek.com/v1",
            model=model_name,
            max_tokens=8192,
        )
    elif model_name in [
        "claude-3.5-haiku",
        "claude-3.5-sonnet",
        "claude-3.7-sonnet",
        "claude-3.7-sonnet-thinking",
        "claude-4-sonnet",
        "claude-4-sonnet-thinking",
        "cursor-small",
        "deepseek-r1-0528",
        "deepseek-v3.1",
        "default",
        "gemini-2.5-flash-preview-05-20",
        "gemini-2.5-pro-preview-05-06",
        "gpt-4.1",
        "gpt-4o",
        "gpt-5",
        "gpt-5-fast",
        "gpt-5-high",
        "gpt-5-high-fast",
        "gpt-5-low",
        "gpt-5-low-fast",
        "gpt-5-mini",
        "gpt-5-nano",
        "grok-3-beta",
        "grok-3-mini",
        "grok-4",
        "kimi-k2-instruct",
        "o3",
        "o3-pro",
        "o4-mini",
    ]:
        apikey = os.getenv("CURSOR_API_KEY")
        return ChatOpenAI(
            api_key=apikey,
            base_url="http://localhost:3010/v1",
            model=model_name,
        )
    else:
        raise ValueError(f"Invalid model name: {model_name}")


if __name__ == "__main__":
    pass
