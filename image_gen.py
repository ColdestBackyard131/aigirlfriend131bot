import aiohttp
import asyncio
import base64
from config import STABLE_HORDE_API_KEY


async def _pollinations(prompt, nsfw=False):
    safe_prompt = prompt.replace(" ", "%20")
    if nsfw:
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=512&height=512&nologo=true&enhance=true"
    else:
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}%20safe%20for%20work?width=512&height=512&nologo=true"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                return await resp.read()
    raise Exception("Pollinations failed")


async def _stable_horde(prompt, nsfw=False):
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

        for _ in range(150):  # max 5 min
            await asyncio.sleep(2)
            async with session.get(f"https://stablehorde.net/api/v2/generate/status/{job_id}") as resp:
                status = await resp.json()
                if status.get("done"):
                    img_b64 = status["generations"][0]["img"]
                    return base64.b64decode(img_b64)

    raise TimeoutError("Stable Horde timed out")


async def generate_image(prompt, nsfw=False):
    # try Pollinations first (fast, instant)
    try:
        return await _pollinations(prompt, nsfw)
    except:
        pass

    # fallback to Stable Horde
    try:
        return await _stable_horde(prompt, nsfw)
    except:
        raise Exception("All image generation failed")
