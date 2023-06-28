"""
Most important module for Aptod.
"""

import re
import platform
import time
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath
import requests
from cpuinfo import get_cpu_info


from .file_suite import FileSuite


class ExtractSuite:
    """
    Finds appimage data from github and gitlab repos.
    """

    def __init__(self):
        self.processor_arch_list = [
            ['aarch64', 'arm64'],
            ['armv7hl', 'armhf', 'arm32'],
            ['x86_64', 'x64', 'amd64', '64bit'],
            ['i386', 'ia32', 'i486', 'i686', 'x86']
        ]

    def compatible_with_my_proccessor(self, file_name):
        """If given file_name includes any processor
        architecture, then choose one that's compatible
        with user proscessor"""

        my_proc = platform.machine()
        if not my_proc:
            my_proc = get_cpu_info()['arch']
        proc_comparation_list = []
        for proc in self.processor_arch_list:
            if isinstance(proc, list) and not my_proc.lower() in proc:
                proc_comparation_list = [*proc_comparation_list, *proc]

        for proc in proc_comparation_list:
            for re_item in re.findall(r'\w+', file_name, re.IGNORECASE):
                # Special treament for x86 and x86_64 confuse
                if proc == 'x86':
                    if 'x86_64' not in re_item and proc in re_item:
                        return False
                elif proc in re_item:
                    return False

        return True

    def nail_version(self, down_url: str) -> str:
        """Takes downloading url as argument,
        and returns url's last part as a name.
        If last part of url doesn't have an version as a
        indentifier, function nails version in name.
        Version in name requried for checking updates."""

        name = down_url.split('/')[-1]
        nums = re.findall('[0-9]+', down_url.split('/')[-2])
        has_version = False

        for num in nums:
            if num in name:
                has_version = True

        if not has_version:
            # in bellow [-1] is AppImage
            word_list = re.findall(r'\w+', name)
            first_word = word_list[-2]

            for proc_list in self.processor_arch_list:
                for proc in proc_list:
                    if proc in first_word:
                        first_word = word_list[-3]
                        break
            name = name.replace(first_word, f'{first_word}-{"-".join(nums)}')

        return name

    def github_extractor(self, owner=None, repo=None, **kwargs) -> dict:
        """Takes Github repo and it's owner as
        arugment. Returns latest appImage data.
        If couldn't find data returns empty dictionary."""

        kwargs_url = kwargs.get('url')
        if kwargs_url:
            owner = PurePosixPath(unquote(urlparse(kwargs_url).path)).parts[1]
            repo = PurePosixPath(unquote(urlparse(kwargs_url).path)).parts[2]

        api_url = f'https://api.github.com/repos/{owner}/{repo}/releases'

        def get_releases(url: str, page: int=1, per_page: int=30) -> list:
            headers = {
                'X-GitHub-Api-Version': '2022-11-28',
                "Accept": "application/vnd.github+json"
            }
            params = {'per_page': per_page, 'page': page}
            res = requests.get(url, headers=headers, params=params, timeout=5)
            res_json = res.json()


            # Let user know, if rate limit ended.
            if res.status_code == 403 and res.headers['X-RateLimit-Remaining'] == '0':
                remaining_time = time.strftime(
                    "%M:%S", time.gmtime(
                        int(res.headers['X-RateLimit-Reset']) - int(time.time())
                    )
                )
                return [{
                    'Error': f"Your hourly Github api rate limit (60) exceeded."
                    f"\nLimit will be reset after {remaining_time} minutes."
                }]
            if res.status_code == 404:
                return [{
                    'Error': f"Not found {owner}/{repo}"
                }]
            # If it's latest release then r.json() is only one item as dict
            if isinstance(res_json, dict):
                return [res_json]
            return res_json

        def app_data(rel_list: list) -> dict:
            """Returns latest release data from list."""

            # Remove prereleased items in r_list
            rel_list = [rel for rel in rel_list if rel['prerelease'] is False]

            for rel in rel_list:
                for asset in rel.get('assets'):
                    # 1) Bellow, If asset matchs with regex, than thats a appimage
                    # 2) If AppImage inlcudes processor arc type than choose compatible one.
                    if (re.search('.AppImage$', asset['name']) and
                        self.compatible_with_my_proccessor(asset['name'])):
                        return {
                            'down_url': asset['browser_download_url']
                        }
            return {}

        # Try for latest, it will not work for most of repos...
        releases = get_releases(api_url + '/latest')

        # If rate limit ends than it will work.
        if releases and releases[0].get('Error'):
            data = releases[0]
            return data

        data = app_data(releases)

        # If latest request gets empty, than make new one thats not only for latest
        if not data:
            page = 0
            per_page = 0
            for _ in range(1):
                page += 1
                per_page += 50
                data = app_data(get_releases(api_url, page=page, per_page=per_page))
                if data:
                    break

        # After above requests, still no data. Than return error message.
        if not data:
            return {'Error': f'No release has been found for appImage at {repo}.'}

        # Get name for data, from down_url
        data['name'] = self.nail_version(data['down_url'])
        return  data

    def gitlab_extractor(self, project_id) -> dict:
        """Takes Gitlab project and it's id as
        arugment. Returns latest appImage data.
        If couldn't find data returns empty dictionary."""

        api_url = f'https://gitlab.com/api/v4/projects/{project_id}/releases/'

        def get_releases(url: str) -> list:
            # Build url

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:102.0)",
            }
            res = requests.get(url, headers=headers, timeout=5)
            res.raise_for_status()

            if isinstance(res.json(), dict):
                return [res.json()]

            return res.json()

        def app_data(rel_list: list) -> dict:
            """Returns latest release data from list."""

            for rel in rel_list:
                for url in rel['assets']['links']:
                # If asset match with re, than that's what we need
                # If there is i386 (32-bit) or aarch keep search for 64-bit
                    if (re.search('.AppImage$', url['name']) and
                        self.compatible_with_my_proccessor(url['name'])):
                        return {
                            'down_url': url['url']
                        }
            return {}

        ## Final part
        releases = get_releases(api_url)
        data = app_data(releases)
        # Get name for data, from down_url
        data['name'] = self.nail_version(data['down_url'])
        return  data

    def is_valid_url(self, url: str):
        """Checks url is valid Github or Gitlab url.
            If url is valid than returns url other wise returns False."""
        github_pattern = r'(https?:\/\/)*(www\.)*github\.com\/[a-zA-Z_0-9-]+\/[a-zA-Z_0-9-]+'
        gitlab_pattern = r'(https?:\/\/)*(www\.)*gitlab\.com\/[a-zA-Z_]+'

        for pattern in [gitlab_pattern, github_pattern]:
            if re.search(pattern, url):
                return url
        return False


    def get(self, app):
        """
        Returns app data or available app list
        """

        apps = {
            'tutanota': lambda: self.github_extractor('tutao', 'tutanota'),
            'vscodium': lambda: self.github_extractor('VSCodium', 'vscodium'),
            'bitwarden': lambda: self.github_extractor('bitwarden', 'bitwarden'),
            'insomnia': lambda: self.github_extractor('Kong', 'insomnia'),
            'keepassxc': lambda: self.github_extractor('keepassxreboot', 'keepassxc'),
            'session': lambda: self.github_extractor('oxen-io', 'session-desktop'),
            'shotcut': lambda: self.github_extractor('mltframework', 'shotcut'),
            'audacity': lambda: self.github_extractor('audacity', 'audacity'),
            'freecad': lambda: self.github_extractor('FreeCAD', 'FreeCAD'),
            'subsurface': lambda: self.github_extractor('subsurface', 'subsurface'),
            'etcher': lambda: self.github_extractor('balena-io', 'etcher'),
            'exifcleaner': lambda: self.github_extractor('szTheory', 'exifcleaner'),
            'hyper': lambda: self.github_extractor('vercel', 'hyper'),
            'electronmail': lambda: self.github_extractor('vladimiry', 'ElectronMail'),
            'musescore': lambda: self.github_extractor('musescore', 'MuseScore'),
            'picocrypt': lambda: self.github_extractor('HACKERALERT', 'Picocrypt'),
            'cryptomator': lambda: self.github_extractor('cryptomator', 'cryptomator'),
            'openvideodownloader': lambda: self.github_extractor('jely2002', 'youtube-dl-gui'),
            'astroffers': lambda: self.github_extractor('hasyee', 'astroffers'),
            'cliniface': lambda: self.github_extractor('frontiersi', 'Cliniface'),
            'appimagelauncher': lambda: self.github_extractor('TheAssassin', 'AppImageLauncher'),
            'aranym': lambda: self.github_extractor('aranym', 'aranym'),
            'appimageupdate': lambda: self.github_extractor('AppImageCommunity', 'AppImageUpdate'),
            'youtube-music': lambda: self.github_extractor('th-ch', 'youtube-music'),
            'appimagepool': lambda: self.github_extractor('prateekmedia', 'appimagepool'),
            'aphototool': lambda: self.github_extractor('aphototool', 'A-Photo-Tool-Libre'),
            'alduin': lambda: self.github_extractor('AlduinApp', 'alduin'),
            'anotherredisdesktopmanager': lambda: self.github_extractor(
                'qishibo', 'AnotherRedisDesktopManager'
            ),
            'appoutlet': lambda: self.github_extractor('appoutlet', 'appoutlet'),
            'arcade-manager': lambda: self.github_extractor('cosmo0', 'arcade-manager'),
            'arduino-ide': lambda: self.github_extractor('arduino', 'arduino-ide'),
            'artisan': lambda: self.github_extractor('artisan-roaster-scope', 'artisan'),
            'auryo': lambda: self.github_extractor('sneljo1', 'auryo'),
            'librewolf': lambda: self.gitlab_extractor(24386000),
            'gameimage': lambda: self.gitlab_extractor(39866323)
        }

        # Return list of avaliable apps
        build_in_apps = apps.keys()
        repo_apps = FileSuite().get_repo()
        avaliable_apps = [*build_in_apps, *repo_apps.keys()]

        if app == 'all':
            return avaliable_apps

        # If app is url...
        if self.is_valid_url(app):
            if 'github' in app:
                return self.github_extractor(url=app)

        if app in build_in_apps:
            return apps[app.lower()]()

        if app in repo_apps:
            return self.github_extractor(url=repo_apps[app])

        return None
