"""
Most important module for Aptod.
"""

import re
import platform
import time
import os
import json
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath
import requests
from cpuinfo import get_cpu_info


from .file_suite import FileSuite
from .data.default_apps import default_apps
from .utils import is_valid_url


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

    def _compatible_with_my_proccessor(self, file_name: str) -> bool:
        """If given file_name includes any processor
        architecture, then check is compatible
        with users proscessor."""
        
        # Find host machine proc arch
        my_proc = platform.machine()
        # Above do not works on some machines but way faster
        if not my_proc:
            my_proc = get_cpu_info()['arch']

        incompatible_arch_list: list = []
        # proc is list
        for proc in self.processor_arch_list:
            # Add arch to incompatible_arch_list if its not compatible with host machine
            if my_proc.lower() not in proc:
                incompatible_arch_list = [*incompatible_arch_list, *proc]
        
        # If file_name includes any incompatible arch type inside its name return false
        for proc in incompatible_arch_list:
            for re_item in re.findall(r'\w+', file_name, re.IGNORECASE):
                # Special treament for x86 and x86_64 confuse
                if proc == 'x86':
                    if 'x86_64' not in re_item and proc in re_item:
                        return False
                elif proc in re_item:
                    return False

        return True

    def _nail_version(self, down_url: str) -> str:
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

    def github_extractor(self, owner=None, repo=None, url=None) -> dict:
        """Takes Github repo and it's owner as arugment or instead 
        directly url for repo. Returns latest release data for appImage."""

   
        if url:
            owner = PurePosixPath(unquote(urlparse(url).path)).parts[1]
            repo = PurePosixPath(unquote(urlparse(url).path)).parts[2]

        api_url = f'https://api.github.com/repos/{owner}/{repo}/releases'

    
        def get_releases(url: str, page: int = 1, per_page: int = 30) -> list:
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
                    f"Limit will be reset after {remaining_time} minutes."
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
                    if (re.search('.AppImage$', asset['name'], re.IGNORECASE) and
                        self._compatible_with_my_proccessor(asset['name'])):
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
        data['name'] = self._nail_version(data['down_url'])
        if url: FileSuite().update_repo(data)
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
                        self._compatible_with_my_proccessor(url['name'])):
                        return {
                            'down_url': url['url']
                        }
            return {}

        ## Final part
        releases = get_releases(api_url)
        data = app_data(releases)
        # Get name for data, from down_url
        data['name'] = self._nail_version(data['down_url'])
        return  data

    

    def get(self, app: str):
        """
        Returns app data or available app list
        """
     
        apps: dict = {}
    
        # Data imported from aptod.data
        for app_ in default_apps:
            if app_['type'] == 'github':
                parsed_path = app_['path'].split('/')
                
                owner, repo = parsed_path[0], parsed_path[1]
                apps.update(
                    {app_['name']: lambda owner=owner, repo=repo: self.github_extractor(owner, repo)})
            else:
                apps.update(
                    {app_['name']: lambda project_id=app_['projectId']: self.gitlab_extractor(project_id)})

        
        # Return list of avaliable apps
        build_in_apps = [_['name'] for _ in default_apps]
        repo_apps = FileSuite().get_repo()
        
        if app == 'all':            
            return [*build_in_apps, *repo_apps.keys()]
        
        # If app is url...
        if isinstance(app, str) and is_valid_url(app):
            if 'github' in app:
                return self.github_extractor(url=app)
        
        if app in build_in_apps:
            return apps[app.lower()]()
        
        if app in repo_apps:
            
            return self.github_extractor(url=repo_apps[app])

        return None
