import os

from openai import OpenAI

client = OpenAI(
    base_url="https://token.sensenova.cn/v1",
    api_key=os.environ["SENSENOVA_API_KEY"],
)

try:
    r = client.images.generate(
        model="sensenova-u1-fast",
        prompt="A clean modern infographic diagram showing a research framework with 3 layers connected by arrows. White background, professional style.",
        size="2048x2048",
        n=1,
    )
    print(f"OK: {r.data[0].url[:80]}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
