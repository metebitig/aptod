"""
Icon related module
"""

import os
import re
import textwrap
from urllib.parse import urljoin
from io import BytesIO
from string import ascii_letters

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
import matplotlib.font_manager


class IconHandler:
    """Find icons for appImage"""
    def __init__(self):
        self.base_url = 'https://appimage.github.io'
        self.home_page = urljoin(self.base_url, '/apps')

    def _get_home_page(self, timeout: int=5) -> str:
        """Request self.home_page and return as text."""
        res = requests.get(self.home_page, timeout=timeout)
        if res.ok:
            return res.text
        return ''

    def _get_home_page_data(self) -> list:
        """Extract all appimage datas from home page."""
        home_page = self._get_home_page()

        if not home_page:
            return []

        soup = BeautifulSoup(home_page, 'html.parser')
        tbody = soup.find('tbody')
        tr_list = tbody.find_all('tr')
        # Extract first a tag in tr elements.
        a_list = [_.find('a') for _ in tr_list]

        page_data = []
        for tag in a_list:
            app_data = {
                "app_name": tag.get_text().strip(),
                "icon_url": tag.find('img').get('src'),
                "app_page_url": urljoin(self.base_url, tag.get('href'))
            }
            page_data.append(app_data)

        return page_data

    def _find_icon(self, app_name: str) -> str:
        """Try find appimage icon from base self.home_page."""
        icon_url = ''
        page_data = self._get_home_page_data()
        for app_data in page_data:

            # appimage.github.io uses placeholder icons for some
            if 'placeholder' in app_data['icon_url']:
                continue

            if re.search(app_name, app_data['app_name'], re.IGNORECASE):
                icon_url = app_data['icon_url']
                break

        return icon_url

    def get_icon(self, app_name: str) -> bytes:
        """If finds image than returns as byte otherwise None."""

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

        if app_name:
            icon_url = self._find_icon(app_name)
        if not icon_url:
            return self.create_icon(app_name)
      
        # Get image.
        res = requests.get(icon_url, stream=True, timeout=5)
        res.raise_for_status()

        # Validate header content type belongs to image.
        if not res.ok or is_content_image(res.headers) is False:
            return self.create_icon(app_name)

        # Last validator, after all.
        try:
            Image.open(BytesIO(res.content))
        except UnidentifiedImageError:
            return self.create_icon(app_name)

        return res.content

    def create_icon(self, text) -> bytes:
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