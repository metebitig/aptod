"""
Utils for Aptod.
"""
import os
import re
import textwrap
from string import ascii_letters
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
import matplotlib.font_manager
import requests
from clint.textui import progress
from .icon_handler import IconHandler


def is_valid_url(url: str):
    """Checks url is valid Github or Gitlab url.
    If url is valid than returns url other wise returns False."""
    github_pattern = r'(https?:\/\/)*(www\.)*github\.com\/[a-zA-Z_0-9-]+\/[a-zA-Z_0-9-]+'
    gitlab_pattern = r'(https?:\/\/)*(www\.)*gitlab\.com\/[a-zA-Z_]+'

    for pattern in [gitlab_pattern, github_pattern]:
        if re.search(pattern, url):
            return url
    return False


def downloader(app_data: dict, timeout=5):
    """Downloads file in given app data url
    to given app data path with progress bar.
    Detects broken downloads and completes them."""

    path = os.path.join(app_data["app_down_path"], app_data['name'])
    path_part = path + '.part'
    app_name = app_data['name']
    down_url = app_data["down_url"]

    # Request for url to get datas.
    res = requests.get(down_url, stream=True, timeout=timeout)
    res.raise_for_status()
    # Two defination is required
    real_length =  int(res.headers.get('content-length'))
    total_length = int(res.headers.get('content-length'))

    # Check file exist and not broken
    if os.path.exists(path):
        if total_length == os.path.getsize(path):
            print(f' {app_name} already downloaded.')
            return

        os.rename(path, app_name + ".part")

    # Check for broken downloads
    elif os.path.exists(path_part):
        missing = real_length - os.path.getsize(path_part)
        if not missing:
            os.rename(path_part, path)
            print('App downloaded')
            return
        # If missing equel to total_length
        # use r without header, otherwise this header throws error
        # missing should'nt be equel to total length
        if missing != total_length:
            res = requests.get(
                down_url,
                stream=True,
                headers={"Range": f"bytes={os.path.getsize(path_part)}-"},
                timeout=timeout)
            total_length = int(res.headers.get('content-length'))
            res.raise_for_status()
            print('.part founded, continuing download...')

    # Final part
    with open(path_part, 'ab') as file:
        print(f'Downloading {app_name}...')
        for chunk in progress.bar(
            res.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1
        ):
            if chunk:
                file.write(chunk)
                file.flush()

    # If all ok, remove .part on filename.
    if (os.path.exists(path_part) and
        real_length == os.path.getsize(path_part)):
        os.rename(path_part, path)



def get_icon(app_name: str) -> bytes:
        """Find, create appImage icons."""

        def create_icon(text) -> bytes:
            """Creates logo for given text and
            returns logo as bytes."""

            longest_word = ''
            for _ in text.split(' '):
                if len(_) > len(longest_word):
                    longest_word = _
            font_size = 40 if len(longest_word) < 8 else (35 if len(longest_word) < 10 else 30)    
        
            text = f"{text}{10 * ' '}"
            width, height = 200, 200
            img = Image.new("RGB", (width, height), "#145DA0")

            font_path = ''
            for _ in matplotlib.font_manager.findSystemFonts(fontpaths=None, fontext='ttf'):
                if 'quicksand-medium' in _.lower():
                    font_path = _
                    break    
            font = ImageFont.truetype(font_path, font_size)   

            avg_char_width = sum(font.getlength(char) for char in ascii_letters) / len(ascii_letters)
            max_char_count = int( (img.size[0] * .95) / avg_char_width )
            scaled_wrapped_text = textwrap.fill(text=text, width=max_char_count)
            d = ImageDraw.Draw(img)
            w, h = d.textbbox((0, 0), scaled_wrapped_text, font=font)[2:]
        
            d.text(
                ((width-w)/2, (height-h)/2), align='center', text=scaled_wrapped_text, fill='white', font=font)
            
            with BytesIO() as output:        
                img.save(output, 'PNG', quality=100)
                image = output.getvalue()

            return image

        def is_content_image(headers: dict) -> bool:
            """Simple content type image validator."""
            image_formats = ["image/png", "image/jpeg", "image/jpg"]
            content_type = ''
            # For ignoring header case
            for key in headers.keys():
                if key.lower() == 'content-type':
                    content_type = key
                    break

            if content_type and headers.get(content_type) in image_formats:
                return True
            return False

        def find_icon(app_name: str) -> str:
            """Try find appimage icon from base self.home_page."""
            icon_url = ''
            page_data = get_home_page_data()
            for app_data in page_data:
                if re.search(app_name, app_data['app_name'], re.IGNORECASE):
                    icon_url = app_data['icon_url']
                    break

            return icon_url

        
        icon_url = find_icon(app_name)
        if not icon_url:
            return create_icon(app_name)

        # Get image.
        res = requests.get(icon_url, stream=True, timeout=5)
        res.raise_for_status()

        # Validate header content type belongs to image.
        if not res.ok or is_content_image(res.headers) is False:
            return create_icon(app_name)

        # Last validator, after all.
        try:
            Image.open(BytesIO(res.content))
        except UnidentifiedImageError:
            return create_icon(app_name)

        return res.content
