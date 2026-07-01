import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.llm.gateway import LLMGateway
from app.config import get_model_for_task

async def main():
    config = get_model_for_task("diagram")
    print(f"API Key configured: {bool(config['api_key'])}")
    print(f"Base URL: {config['base_url']}")
    print(f"Model: {config['model']}")

    gw = LLMGateway()
    gw.configure(api_key=config["api_key"], base_url=config["base_url"], model_name=config["model"])
    result = await gw.generate_image(prompt="A simple flowchart with 3 boxes connected by arrows. White background.")
    print(f"Result: {result.get('status')}: {result.get('url', result.get('error', ''))[:100]}")

asyncio.run(main())
