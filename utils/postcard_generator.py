
import random

def generate_postcard_html(destination, message=None, sender_name="A Wanderer"):
    """
    Generates a styled HTML postcard.
    """
    if not message:
        message = f"Greetings from beautiful {destination}! Having the time of my life exploring this amazing place. Wish you were here!"
        
    # Unsplash Source was deprecated, using a reliable placeholder or just a stylized div
    # using 'picsum' or similar might be risky if they change.
    # We will use a gradient background if no image, or try to use a generic travel image.
    
    # Let's try to get a keyword based image from a free placeholder service that supports keywords
    # "https://loremflickr.com/600/400/{destination},travel"
    
    image_url = f"https://loremflickr.com/600/400/{destination.replace(' ', ',')},landscape/all"
    
    rotation = random.randint(-2, 2)
    
    html = f"""
    <div style="
        font-family: 'Courier New', monospace;
        background-color: #fcfcfc;
        padding: 20px;
        border: 1px solid #ddd;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.2);
        max-width: 600px;
        margin: 20px auto;
        transform: rotate({rotation}deg);
        position: relative;
    ">
        <div style="
            position: absolute;
            top: 20px;
            right: 20px;
            width: 80px;
            height: 100px;
            border: 2px dashed #ccc;
            background-color: #eee;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #aaa;
            font-size: 10px;
        ">STAMP</div>
        
        <h2 style="
            font-family: 'Brush Script MT', cursive;
            color: #e74c3c;
            font-size: 40px;
            margin-top: 0;
            text-align: center;
            text-shadow: 1px 1px 2px #aaa;
        ">Greetings from {destination}</h2>
        
        <div style="display: flex; gap: 20px; margin-top: 20px;">
            <div style="flex: 1;">
                <img src="{image_url}" style="
                    width: 100%; 
                    height: auto; 
                    border-radius: 4px; 
                    border: 4px solid white; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                " alt="{destination}">
            </div>
            <div style="flex: 1; padding-top: 20px; font-size: 16px; line-height: 1.6; color: #333;">
                <p>{message}</p>
                <br>
                <p style="text-align: right;">- {sender_name}</p>
            </div>
        </div>
        
        <div style="
            margin-top: 20px; 
            font-size: 10px; 
            color: #ccc; 
            text-align: center; 
            border-top: 1px solid #eee; 
            padding-top: 10px;
        ">
            Sent via WanderTrip AI
        </div>
    </div>
    """
    return html

def get_ai_postcard_message(client, destination, vibe="Fun"):
    """
    Uses LLM to generate a catchy postcard message.
    """
    try:
        prompt = f"Write a short, catchy postcard message (max 3 sentences) from {destination}. Vibe: {vibe}."
        res = client.chat.completions.create(
            model="qwen/qwen3-32b", # Fast model
            messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content.replace('"', '')
    except:
        return f"Having a blast in {destination}!"
