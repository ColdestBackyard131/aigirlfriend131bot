import aiohttp
import asyncio
import base64
from config import STABLE_HORDE_API_KEY

QUALITY_SUFFIX = (
    ", ultra realistic, 4k, sharp focus, professional photography, "
    "canon eos r5, 85mm lens, natural skin texture, highly detailed face, "
    "cinematic lighting, instagram photo"
)

NEGATIVE = (
    "cartoon, anime, illustration, painting, drawing, fake, cgi, 3d render, "
    "blurry, low quality, watermark, text, ugly, deformed, bad anatomy"
)


async def _pollinations(prompt, nsfw=False):
    full_prompt = prompt + QUALITY_SUFFIX
    neg = NEGATIVE
    safe_prompt = full_prompt.replace(" ", "%20").replace(",", "%2C")
    safe_neg = neg.replace(" ", "%20").replace(",", "%2C")

    url = (
        f"https://image.pollinations.ai/prompt/{safe_prompt}"
        f"?negative={safe_neg}"
        f"&width=832&height=1216"
        f"&nologo=true&enhance=true&model=flux"
        f"&seed={asyncio.get_event_loop().time().__int__()}"
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status == 200:
                data = await resp.read()
                if len(data) > 10000:  # make sure it's a real image not an error page
                    return data
    raise Exception("Pollinations failed or returned invalid image")


async def _stable_horde(prompt, nsfw=False):
    url = "https://stablehorde.net/api/v2/generate/async"
    payload = {
        "prompt": prompt + QUALITY_SUFFIX,
        "nsfw": nsfw,
        "censor_nsfw": not nsfw,
        "models": ["Realistic Vision"],
        "params": {
            "steps": 30,
            "cfg_scale": 7,
            "width": 832,
            "height": 1216,
            "negative_prompt": NEGATIVE,
            "karras": True,
            "sampler_name": "k_dpmpp_2m"
        }
    }
    headers = {"apikey": STABLE_HORDE_API_KEY, "Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            data = await resp.json()
            job_id = data["id"]

        for _ in range(150):
            await asyncio.sleep(2)
            async with session.get(
                f"https://stablehorde.net/api/v2/generate/status/{job_id}"
            ) as resp:
                status = await resp.json()
                if status.get("done"):
                    img_b64 = status["generations"][0]["img"]
                    return base64.b64decode(img_b64)

    raise TimeoutError("Stable Horde timed out")


async def generate_image(prompt, nsfw=False):
    try:
        return await _pollinations(prompt, nsfw)
    except:
        pass
    try:
        return await _stable_horde(prompt, nsfw)
    except:
        raise Exception("All image generation failed")
