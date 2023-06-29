"""
Icon Finder Module
"""
from urllib.parse import urljoin
import re
from io import BytesIO
import requests
from bs4 import BeautifulSoup
from PIL import Image, UnidentifiedImageError

class AppimageIconRepoFinder:
    """Find icons for appImage"""
    def __init__(self):
        self.base_url = 'https://appimage.github.io'
        self.home_page = urljoin(self.base_url, '/apps')


    def get_home_page(self, timeout: int=5):
        """Request self.home_page and return as text."""
        res = requests.get(self.home_page, timeout=timeout)
        if res.ok:
            return res.text
        return None

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

        def is_content_image(headers):
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




if __name__ == "__main__":
    finder = AppimageIconRepoFinder()
    icon_url = finder.get_icon_as_bytes('etcher')
