from openai import OpenAI

client = OpenAI(
    base_url="https://token-plan-cn.xiaomimimo.com/v1",
    api_key="tp-clz6ojk7e7tdmgaygwfs8f3apbplzqqyj69qqtli2nk6bdb2",
)

try:
    resp = client.chat.completions.create(
        model="mimo-v2.5-pro",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=10,
    )
    print(f"Model: {resp.model}")
    print(f"Content: {resp.choices[0].message.content}")
    print(f"Usage: {resp.usage}")
    print("OK!")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
