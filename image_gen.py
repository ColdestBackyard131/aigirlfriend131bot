import asyncio
import aiohttp
import base64
from config import STABLE_HORDE_API_KEY


async def generate_image(prompt, nsfw=False):
    url = "https://stablehorde.net/api/v2/generate/async"
    payload = {
        "prompt": prompt,
        "nsfw": nsfw,
        "models": ["SDXL 1.0"],
        "params": {"steps": 20}
    }
    headers = {"apikey": STABLE_HORDE_API_KEY, "Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            data = await resp.json()
            job_id = data["id"]

        # poll for result without blocking
        for _ in range(150):  # max 5 min wait
            await asyncio.sleep(2)
            async with session.get(f"https://stablehorde.net/api/v2/generate/status/{job_id}") as resp:
                status = await resp.json()
                if status.get("done"):
                    img_b64 = status["generations"][0]["img"]
                    return base64.b64decode(img_b64)

    raise TimeoutError("Image generation timed out")
