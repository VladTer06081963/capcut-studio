import asyncio
from capcut.render.kie_client import KieClient
from capcut.lib.config import load_dotenv
import os

async def main():
    load_dotenv()
    api_key = os.getenv("KIE_API_KEY")
    if not api_key:
        return
    client = KieClient(api_key=api_key)
    models = ["kling/v2-1-standard", "bytedance/v1-lite-text-to-video", "wan/2-2-a14b-text-to-video-turbo", "hailuo/02-text-to-video-standard", "runway"]
    for m in models:
        try:
            price = client.get_model_price(m)
            print(f"Model: {m}, Price: {price}")
        except Exception as e:
            pass

if __name__ == "__main__":
    asyncio.run(main())
