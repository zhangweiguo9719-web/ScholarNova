import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.llm.gateway import LLMGateway
from app.config import settings, get_model_for_task

async def main():
    config = get_model_for_task("diagram")
    print(f"API Key: {config['api_key'][:10] if config['api_key'] else 'EMPTY'}...")
    print(f"Base URL: {config['base_url']}")
    print(f"Model: {config['model']}")

    gw = LLMGateway()
    gw.configure(
        api_key=config["api_key"],
        base_url=config["base_url"],
        model_name=config["model"],
    )

    result = await gw.generate_image(prompt="A simple flowchart: Data -> Processing -> Output. White background.")
    print(f"Result: {result}")

asyncio.run(main())
