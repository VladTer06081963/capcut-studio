import asyncio
from py.render.kie_client import KieClient
from py.lib.config import load_dotenv
import os

async def main():
    load_dotenv()
    api_key = os.getenv("KIE_API_KEY")
    if not api_key:
        return
    client = KieClient(api_key=api_key)
    models = ["wan/3-0-video-prime", "wan/3-0-video"]
    for m in models:
        try:
            price = client.get_model_price(m)
            print(f"Model: {m}, Price: {price}")
        except Exception as e:
            pass

if __name__ == "__main__":
    asyncio.run(main())
