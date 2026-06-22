import requests
import time
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
    response = requests.post(url, json=payload, headers=headers)
    job_id = response.json()["id"]

    while True:
        status = requests.get(f"https://stablehorde.net/api/v2/generate/status/{job_id}").json()
        if status["done"]:
            img_b64 = status["generations"][0]["img"]
            return base64.b64decode(img_b64)
        time.sleep(2)


def generate_local(prompt, negative_prompt="", steps=20):
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "sampler_index": "DPM++ 2M Karras",
        "width": 512,
        "height": 512
    }
    response = requests.post("http://127.0.0.1:7860/sdapi/v1/txt2img", json=payload)
    img_b64 = response.json()["images"][0]
    return base64.b64decode(img_b64)
