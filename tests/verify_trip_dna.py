import sys
import os
import textwrap

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.trip_dna import render_trip_dna_html

def test_html_rendering():
    mock_data = {
        "archetypes": [
            { "name": "Explorer", "percentage": 50, "reason": "Loves discovery" },
            { "name": "Foodie", "percentage": 30, "reason": "Eats everything" }
        ],
        "dominant_type": "Explorer",
        "tagline": "The Wonderer",
        "travel_spirit_animal": "Fox",
        "recommendation": "Kyoto"
    }
    
    html = render_trip_dna_html(mock_data)
    print("--- RAW HTML ---")
    try:
        print(html)
    except UnicodeEncodeError:
        print(html.encode('ascii', 'ignore').decode('ascii'))
    print("--- END RAW HTML ---")
    
    # Check for indentation issues
    lines = html.split('\n')
    if lines[1].startswith('            '): # Check for 12 spaces
        print("⚠️ Detected Validation Indentation")
    else:
        print("✅ No excessive indentation detected")

if __name__ == "__main__":
    test_html_rendering()
