
import os
from groq import Groq

def transcribe_audio(audio_bytes):
    """
    Transcribes audio bytes using Groq's Whisper implementation.
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    try:
        # Groq API requires a filename/file-like object with a name
        # We can't just send raw bytes sometimes, but client.audio.transcriptions.create
        # usually accepts (filename, file) tuple.
        
        transcription = client.audio.transcriptions.create(
            file=("voice_input.wav", audio_bytes),
            model="whisper-large-v3-turbo",
            response_format="json",
            temperature=0.0
        )
        
        return transcription.text
    except Exception as e:
        # Fallback or error logging
        print(f"Transcription Error: {e}")
        return None
