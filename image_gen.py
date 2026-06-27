import aiohttp
import asyncio
import base64
import random
from config import STABLE_HORDE_API_KEY

QUALITY_SUFFIX = (
    ", real human, photorealistic, hyperrealistic, 8k uhd, shot on sony a7r5, "
    "85mm f1.4 lens, natural skin pores, real skin texture, subsurface scattering, "
    "sharp eyes, detailed face, cinematic color grading, instagram model photo, "
    "professional photography, perfect lighting"
)

NEGATIVE = (
    "cartoon, anime, illustration, painting, cgi, 3d render, digital art, "
    "blurry, low quality, watermark, text, logo, ugly, deformed, mutated, "
    "bad anatomy, bad hands, extra fingers, disfigured, plastic skin, "
    "fake looking, unrealistic, airbrushed, overexposed, underexposed, "
    "duplicate, clone, multiple people"
)


def _unique_seed():
    return random.randint(100000, 999999999)


async def _pollinations(prompt, nsfw=False):
    seed = _unique_seed()
    full_prompt = prompt + QUALITY_SUFFIX
    safe_prompt = full_prompt.replace(" ", "%20").replace(",", "%2C").replace("(", "%28").replace(")", "%29")
    safe_neg = NEGATIVE.replace(" ", "%20").replace(",", "%2C")

    url = (
        f"https://image.pollinations.ai/prompt/{safe_prompt}"
        f"?negative={safe_neg}"
        f"&width=832&height=1216"
        f"&nologo=true&enhance=true&model=flux"
        f"&seed={seed}"
        f"&safe={'false' if nsfw else 'true'}"
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=90)) as resp:
            if resp.status == 200:
                data = await resp.read()
                if len(data) > 15000:
                    return data
    raise Exception("Pollinations failed")


async def _stable_horde(prompt, nsfw=False):
    seed = _unique_seed()
    url = "https://stablehorde.net/api/v2/generate/async"
    payload = {
        "prompt": prompt + QUALITY_SUFFIX + f" ### {NEGATIVE}",
        "nsfw": nsfw,
        "censor_nsfw": not nsfw,
        "models": ["Realistic Vision"],
        "params": {
            "steps": 35,
            "cfg_scale": 7.5,
            "width": 832,
            "height": 1216,
            "seed": str(seed),
            "karras": True,
            "sampler_name": "k_dpmpp_2m",
            "hires_fix": True,
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
