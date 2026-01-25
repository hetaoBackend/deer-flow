import argparse
import base64
import os

import requests


def generate_image(prompt: str, output_path: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "GEMINI_API_KEY is not set"
    response = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent",
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "generationConfig": {"imageConfig": {"aspectRatio": "9:16"}},
            "contents": [{"parts": [{"text": prompt}]}],
        },
    )
    parts: list[dict] = response.json()["candidates"][0]["content"]["parts"]
    image_parts = [part for part in parts if part.get("inlineData", False)]
    if len(image_parts) == 1:
        base64_image = image_parts[0]["inlineData"]["data"]
        # Save the image to a file
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(base64_image))
        return f"Successfully generated image to {output_path}"
    else:
        return "Failed to generate image"


def main(input_path: str, output_path: str):
    with open(
        input_path,
        "r",
    ) as f:
        raw = f.read()
        print(generate_image(raw, output_path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Doraemon comic image")
    parser.add_argument("--input_path", required=True, help="Path to the input prompt JSON file")
    parser.add_argument("--output_path", required=True, help="Path to save the output image")
    args = parser.parse_args()
    main(args.input_path, args.output_path)
