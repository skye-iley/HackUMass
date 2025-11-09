import os
from elevenlabs import ElevenLabs, play
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("ELEVEN_LABS_KEY")

def text_to_speech_save_file(text, filename="output.mp3"):
    client = ElevenLabs(api_key=API_KEY)
    #print(text)
    audio = client.text_to_speech.convert(
        text=text,
        voice_id="Xb7hH8MSUJpSbSDYk0k2",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )
    try:
        audio_bytes = b"".join(audio)  # Join generator chunks into bytes
    except:
        print("out of tokens")
        return None
    with open(filename, "wb") as f:
        f.write(audio_bytes)
    print(f"Audio saved to {filename}")
if __name__ == "__main__":
    # Example usage:
    text_to_speech_save_file("Hello, this is a test of ElevenLabs text-to-speech API.")

    from elevenlabs import ElevenLabs

    client = ElevenLabs(api_key=API_KEY)
    voices = client.voices.get_all()
    for voice in voices.voices:
        print(f"{voice.name}: {voice.voice_id}")
