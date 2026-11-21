
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("MURF_API_KEY")

# Murf India streaming endpoint
URL = "https://in.api.murf.ai/v1/speech/stream"

print("\n====================================")
print(" YATRAPILOT AI - MURF FALCON TEST")
print("====================================")

if not API_KEY:
    raise ValueError("MURF_API_KEY missing in .env")

# Text to convert into speech
payload = {
    "text": (
        "Hello! Welcome to YatraPilot AI. "
        "I am your intelligent travel assistant. "
        "Tell me your destination, and I will help "
        "you plan an amazing journey."
    ),
    "voiceId": "en-US-natalie",
    "model": "falcon-2.1",
    "locale": "en-US",
    "format": "MP3",
    "channelType": "MONO",
    "sampleRate": 24000
}

headers = {
    "api-key": API_KEY,
    "Content-Type": "application/json"
}

try:
    print("\nConnecting to Murf Falcon 2.1...")

    with requests.post(
        URL,
        headers=headers,
        json=payload,
        stream=True,
        timeout=90
    ) as response:

        print("HTTP Status:", response.status_code)

        if response.status_code == 200:
            output_file = "yatra_voice_test.mp3"

            total_bytes = 0

            with open(output_file, "wb") as audio:
                for chunk in response.iter_content(
                    chunk_size=8192
                ):
                    if chunk:
                        audio.write(chunk)
                        total_bytes += len(chunk)

            if total_bytes == 0:
                raise RuntimeError("Murf returned an empty audio file")

            print("\nSUCCESS: Murf API connected!")
            print("Model: Falcon 2.1")
            print("Audio size:", total_bytes, "bytes")
            print("Saved:", output_file)
            print("\nMURF API TEST PASSED!")

        else:
            print("\nMURF API TEST FAILED")
            print("Response:", response.text[:1000])

except requests.exceptions.RequestException as error:
    print("\nNETWORK ERROR:", error)

except Exception as error:
    print("\nERROR:", error)

print("\n====================================")
