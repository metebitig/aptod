"""
Utils for Aptod.
"""
import os
import requests
from clint.textui import progress




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
