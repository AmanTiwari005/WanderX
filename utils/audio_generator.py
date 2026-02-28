
from io import BytesIO
try:
    from gtts import gTTS
except ImportError:
    gTTS = None

def generate_pronunciation(text, lang='en'):
    """
    Generates pronunciation audio for a given text using gTTS.
    Returns BytesIO object containing MP3 data.
    """
    if not gTTS:
        return None
        
    try:
        tts = gTTS(text=text, lang=lang)
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except Exception as e:
        print(f"TTS Error: {e}")
        return None
