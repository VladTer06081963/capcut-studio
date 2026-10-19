import asyncio
from py.render.kie_client import KieClient
from py.lib.config import load_dotenv
import os

async def main():
    load_dotenv()
    api_key = os.getenv("KIE_API_KEY")
    if not api_key:
        print("NO API KEY")
        return
    client = KieClient(api_key=api_key)
    models = client.list_models()
    for m in models:
        if "kling" in m.model.lower() or "video" in m.model.lower() or "minimax" in m.model.lower() or "runway" in m.model.lower() or "luma" in m.model.lower() or "hailuo" in m.model.lower():
            try:
                price = client.get_model_price(m.model)
                print(f"Model: {m.model}, Price: {price.get('creditsPerRun', 'N/A')}")
            except Exception as e:
                pass

if __name__ == "__main__":
    asyncio.run(main())
