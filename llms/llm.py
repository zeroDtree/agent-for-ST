from langchain_openai import ChatOpenAI


def get_llm_model(
    model_name: str,
    base_url: str,
    apikey: str,
    max_tokens: int = 8192,
    streaming: bool = True,
    temperature: float = 1,
    presence_penalty: float = 0,
    frequency_penalty: float = 0,
):
    return ChatOpenAI(
        api_key=apikey,
        base_url=base_url,
        model=model_name,
        max_tokens=max_tokens,
        streaming=streaming,
        temperature=temperature,
        model_kwargs={},
        presence_penalty=presence_penalty,
        frequency_penalty=frequency_penalty,
    )


if __name__ == "__main__":
    pass
