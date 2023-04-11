from PIL import Image, ImageDraw, ImageFont
import textwrap
import os
from string import ascii_letters
from io import BytesIO

 
def logo_generator(text):
    """Creates logo for given text and
    returns logo as bytes."""

    text = text + '\n by Aptod' 
    width, height = 200, 200
    img = Image.new("RGB", (width, height), "#145DA0")
    font = ImageFont.truetype(f'{os.path.dirname(__file__)}/data/Lobster-Regular.ttf', 35)

    avg_char_width = sum(font.getsize(char)[0] for char in ascii_letters) / len(ascii_letters)
    max_char_count = int( (img.size[0] * .95) / avg_char_width )
    scaled_wrapped_text = textwrap.fill(text=text, width=max_char_count)

    d = ImageDraw.Draw(img)
    w, h = d.textsize(scaled_wrapped_text, font=font)
    h += int(h*0.21)
    d.text(((width-w)/2, (height-h)/2), align='center', text=scaled_wrapped_text, fill='white', font=font)
    
    with BytesIO() as output:        
        img.save(output, 'PNG', quality=100)
        data = output.getvalue()
    
    return data
    
