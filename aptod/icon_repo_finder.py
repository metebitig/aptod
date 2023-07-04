"""
https://appimage.github.io
realted module
"""

from urllib.parse import urljoin
import re
from io import BytesIO
import pathlib
from pathlib import Path
import os
import requests
from bs4 import BeautifulSoup
from PIL import Image, UnidentifiedImageError
import yaml


class AppimageIconRepoFinder:
    """Find icons for appImage"""
    def __init__(self):
        self.base_url = 'https://appimage.github.io'
        self.home_page = urljoin(self.base_url, '/apps')

    def get_home_page(self, timeout: int=5) -> str:
        """Request self.home_page and return as text."""
        res = requests.get(self.home_page, timeout=timeout)
        if res.ok:
            return res.text
        return ''

    def get_home_page_data(self) -> list:
        """Extract all appimage datas from home page."""
        home_page = self.get_home_page()

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

    def find_icon(self, app_name: str) -> str:
        """Try find appimage icon from base self.home_page."""
        icon_url = ''
        page_data = self.get_home_page_data()
        for app_data in page_data:
            if re.search(app_name, app_data['app_name'], re.IGNORECASE):
                icon_url = app_data['icon_url']
                break

        return icon_url

    def get_icon_as_bytes(self, app_name: str='', icon_url: str=''):
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
            icon_url = self.find_icon(app_name)
        if not icon_url:
            return None

        # Get image.
        res = requests.get(icon_url, stream=True, timeout=5)
        res.raise_for_status()

        # Validate header content type belongs to image.
        if not res.ok or is_content_image(res.headers) is False:
            return None

        # Last validator, after all.
        try:
            Image.open(BytesIO(res.content))
        except UnidentifiedImageError:
            return None

        return res.content

    def download_repostory(self) -> list:
        """Crate repostory from appimage.github.io data"""

        def md_to_yaml_to_dict(file):
            '''Takes md file and extracts yaml and converts to dict.'''

            with open(file, 'r', encoding='utf-8') as md_file:
                lines = md_file.readlines()
                new_lines = []

                yaml_dash = 0
                for line in lines:
                    if line.strip() == '---':
                        yaml_dash += 1
                        if yaml_dash > 1:
                            break
                        else:
                            continue

                    new_lines.append(line)

                yaml_text = ''.join(new_lines)
                data = ''
                try:
                    data = yaml.load(yaml_text, Loader=yaml.SafeLoader)
                # 1300+ file exist and 70 one gives error
                # Just pass
                except yaml.scanner.ScannerError:
                    pass
                except yaml.parser.ParserError:
                    pass

                return data

        def process_file(file) -> dict:
            yaml_dict = md_to_yaml_to_dict(file)
            if yaml_dict and yaml_dict['links']:
                if yaml_dict['links'][0]['type'] == 'GitHub' and yaml_dict['desktop']:
                    appimage_name = yaml_dict['desktop']['Desktop Entry']['Name']
                    url = urljoin('https://www.github.com', yaml_dict['links'][0]['url'])

                    icon_url = yaml_dict.get('icons')
                    if icon_url:
                        icon_url = urljoin('https://appimage.github.io/database/', yaml_dict['icons'][0])

                    appimage_data = {
                        'name': appimage_name,
                        'type': 'Github',
                        'url': url,
                        'comment': yaml_dict['desktop']['Desktop Entry'].get('Comment'),
                        'categorie': yaml_dict['desktop']['Desktop Entry'].get('Categories'),
                        'icon_url': icon_url,                     
                    }
                    return appimage_data

            return {}
            

        source_dir = Path(os.path.join(pathlib.Path(__file__).parent.resolve(), '../apps'))
        files = source_dir.iterdir()
        repo = []
        for file in files:
            data = process_file(file)
            if data:
                repo.append(data)
                
        return repo


if __name__ == "__main__":
    finder = AppimageIconRepoFinder()
    # icon_url = finder.get_icon_as_bytes('etcher')
    finder.download_repostory()
