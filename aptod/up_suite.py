"""Important update related Aptod module."""

import os

from .utils import downloader
from .extract_suite import ExtractSuite

class UpSuite:
    """Update related Aptod module. Checks updates and
    makes upgrades."""
    def __init__(self):
        self.extractor = ExtractSuite()

    def has_update(self, app_path: str) -> dict:
        """Takes app data from extractor,
        and takes local app data from file
        suite. Checks if file is to old to date.
        If there is a update returns app data
        that comes from extractor."""

        app_list = self.extractor.get('all')
        for app in app_list:
            if app.lower() in app_path.lower() or app.lower().replace('-', '') in app_path.lower():
                app_name = app
                break

        if app_name:
            app_data = self.extractor.get(app_name)
            if app_data.get('Error'):
                return app_data

        down_name = app_data.get('name')

        # If there is update return app_data
        # cause, otherwise we have to do second request for app_data
        if app_path.split('/')[-1] in down_name:
            return {}
        return app_data

    def update_app(self, app_data: dict):
        """Downloads new version of app,
        and deletes old version of app."""

        # Download app, if problems occur than remove
        try:
            downloader(app_data)
        except Exception:
            os.remove(app_data['app_down_path'])
            raise
        else:
            # Everythinks looks fine so delete old app
            os.remove(app_data['app_cur_path'])
