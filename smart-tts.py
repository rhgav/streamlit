import requests

response = requests.post(
    f"https://api.stability.ai/v2beta/stable-image/generate/sd3",
    headers={
        "authorization": f"sk-ORKpxhAiCCqv6UZ5GGfyL8JHv2hEBWQ3mLapVdXJZWBVn6ie",
        "accept": "image/*"
    },
    files={"none": ''},
    data={
        "prompt": "An blue ship with golden wings",
        "output_format": "jpeg",
    },
)

if response.status_code == 200:
    with open("./blue_ship_with_golden_wings.jpeg", 'wb') as file:
        file.write(response.content)
else:
    raise Exception(str(response.json()))


from PIL import Image

input_image = Image.open("./blue_ship_with_golden_wings.jpeg").convert("RGB")
print(input_image)
