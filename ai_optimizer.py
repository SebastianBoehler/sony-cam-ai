import os
import base64
import json  # Add this import
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def optimize_camera_settings(image_path, prompt, initial_settings, available_settings):
    base64_image = encode_image(image_path)

    # Convert exposure_compensation to a list if it's an integer
    if isinstance(available_settings.get("exposure_compensation"), int):
        available_settings["exposure_compensation"] = [
            available_settings["exposure_compensation"]
        ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are an expert photographer assistant. Analyze the image and provide optimal camera settings based on the given prompt, current settings, and available options. Respond with a JSON object containing the suggested settings.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Analyze this image and provide optimal camera settings for the following prompt: {prompt}. Current settings: {json.dumps(initial_settings, indent=2)}. Available settings: {json.dumps(available_settings, indent=2)}",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            },
        ],
        functions=[
            {
                "name": "set_camera_settings",
                "description": "Set the optimal camera settings based on the image analysis",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "shutter_speed": {
                            "type": "string",
                            "description": "The recommended shutter speed",
                            "enum": available_settings.get("shutter_speed", []),
                        },
                        "aperture": {
                            "type": "string",
                            "description": "The recommended aperture value",
                            "enum": available_settings.get("aperture", []),
                        },
                        "iso": {
                            "type": "string",
                            "description": "The recommended ISO value",
                            "enum": available_settings.get("iso", []),
                        },
                        "white_balance": {
                            "type": "string",
                            "description": "The recommended white balance setting",
                            "enum": available_settings.get("white_balance", []),
                        },
                        "focus_mode": {
                            "type": "string",
                            "description": "The recommended focus mode",
                            "enum": available_settings.get("focus_mode", []),
                        },
                        "exposure_compensation": {
                            "type": "number",
                            "description": "The recommended exposure compensation value",
                            "enum": [
                                float(x)
                                for x in available_settings.get(
                                    "exposure_compensation", []
                                )
                            ],
                        },
                        "zoom": {
                            "type": "number",
                            "description": "The recommended zoom level (increase for a closer view)",
                            "minimum": available_settings.get("zoom", {}).get("min", 1),
                            "maximum": available_settings.get("zoom", {}).get(
                                "max", 100
                            ),
                        },
                    },
                    "required": ["shutter_speed", "aperture", "iso", "zoom"],
                },
            }
        ],
        function_call={"name": "set_camera_settings"},
        max_tokens=300,
    )

    return response.choices[0].message.function_call.arguments


# Example usage:
# result = optimize_camera_settings("path/to/image.jpg", "Capture a vibrant sunset over the ocean")
# print(result)
