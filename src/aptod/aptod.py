"""
Aptod class and cli dialogs.
"""

import os
import re
import time
from collections import OrderedDict
import argparse
from simple_term_menu import TerminalMenu

from .utils import downloader, is_valid_url
from .extract_suite import ExtractSuite
from .up_suite import UpSuite
from .file_suite import FileSuite

__version__ = "0.0.1"


APP_LIST =  ExtractSuite().get('all')

def show_categories_menu():
    """Show download menu."""
    unofficial_apps = FileSuite().get_repo(unofficial=True)
    categories = list(dict.fromkeys([_['categorie'] for _ in unofficial_apps]))
    
    categories_menu = TerminalMenu(
        categories,
        show_multi_select_hint=True,
        menu_cursor_style=("fg_green", "bold"),
        title='CATEGORIES:')
    
    menu_entry_index = categories_menu.show()
    
    categorie = categories[menu_entry_index]
    categoried_apps = []
    categoried_apps_clean = []

    for app in unofficial_apps:
        if app['categorie'] == categorie:
            categoried_apps_clean.append(app)
            categoried_apps.append(
                f"{app['name']} ({app['comment']}) ({app['url']})".replace('(None)', ''))

    unoffical_apps_menu = TerminalMenu(
        categoried_apps,
        multi_select=True,
        show_multi_select_hint=True,
        menu_cursor_style=("fg_green", "bold"),
        title=f'{categorie} APPS:')

    chosen_indexes = unoffical_apps_menu.show()
    chosens = [categoried_apps_clean[_] for _ in chosen_indexes]

    return chosens

def download_menu():
    """Show download menu."""
    terminal_menu = TerminalMenu(
        APP_LIST,
        multi_select=True,
        show_multi_select_hint=True,
        menu_cursor_style=("fg_green", "bold"),
        title='Select for download:')
    
    terminal_menu.show()
    menu_entry_index = terminal_menu.chosen_menu_entries
    return list(menu_entry_index)

def remove_menu():
    """Show remove menu."""
    terminal_menu = TerminalMenu(
        Aptod().installed_apps(),
        multi_select=True,
        show_multi_select_hint=True,
        menu_cursor_style=("fg_green", "bold"),
        title='Select for REMOVE:')

    terminal_menu.show()
    menu_entry_index = terminal_menu.chosen_menu_entries
    return list(menu_entry_index)


class Aptod:
    def __init__(self):
        self.file_suite = FileSuite()
        self.update_suite = UpSuite()
        self.apps = APP_LIST

        data = self.file_suite.get_config()
        if not data:
            self.file_suite.create_config()
            data = self.file_suite.get_config()
        self.main_folder = data['MainFolder']

    def install_aptod(self):
        """Create config file, exist config file means Aptod is installed."""
        # If config file exists, app is intalled.
        if self.file_suite.get_config():
            return print('Aptod is already installed.')
            
        self.file_suite.create_config()


    def installed_apps(self):
        """Returns installed app names as list."""

        # Get all appimage names in MainFolder
        installed_appimages = {}
        apps_folder = self.file_suite.get_main_app_dir()

        # If not appImage folder exist we will consider there is no app to update
        if not os.path.exists(apps_folder):
            return []

        for dir_ in os.listdir(apps_folder):
            # Requried for errors
            if not os.path.isfile(dir_):
                for file in os.listdir(os.path.join(apps_folder, dir_)):
                    if file.lower().endswith('.appimage'):
                        installed_appimages[file] = apps_folder + '/' + dir_ + '/' + file
                        break

        # Convert appimage names to simple app name
        # Exmp. tutanota-desktop-linux-3-106-5.appimage > tutanota
        # And create dictionary with three data, file_name, name, file_path
        installed_apps = {}

        for file_name, file_path in installed_appimages.items():

            for app in self.apps:
                if (app.lower() in file_name.lower() or
                    app.lower().replace('-', '') in file_name.lower()):
                    installed_apps[app] = {
                        'file_name': file_name,
                        'file_path': file_path,
                    }
                    break
        return installed_apps

    def update_apps(self, **kwargs):
        """Update handler for installed apps."""
        installed = self.installed_apps()
        app_list = installed
        if not app_list:
            print('Currently you don\'t have an installed app tp update.')
            return
        if kwargs.get('app_list'):
            app_list = kwargs.get('app_list')
        for app in app_list:
            app_path = installed[app]['file_path']
            app_name = installed[app]['file_name']
            app_data = self.update_suite.has_update(app_path)
            # If functions returns data, there is a update
            if app_data.get('Error'):
                print(f"{app_data['Error']}", end='\r')
            elif app_data:
                print(f'❌ {app} is old to date.')
                if kwargs.get('operation') == 'update':
                    app_data['app_down_path'] = app_path.replace(app_name, '')
                    app_data['app_cur_path'] = app_path
                    self.update_suite.update_app(app_data)
                    self.file_suite.create_desktop(app_data)
            else:
                print(f'✅ {app} is up to date.')

    def install_app(self, app_name: list = [], app_data: dict = {}) -> None:
        """Installas apps, creates logos, desktop files for them."""

        def installer(app_data):
            if isinstance(app_data, dict) and app_data.get('Error'):
                print(app_data['Error'])
                return

            # Create folder with app name
            # Make first letter capital
            app = ''.join(re.findall(r'\w+', app_data['name'])[:2])
            down_path = os.path.join(self.main_folder, app)
            if not os.path.exists(down_path):
                os.makedirs(down_path)
            app_data['app_down_path'] = down_path
            downloader(app_data)
            # Create .desktop for integration
            self.file_suite.create_desktop(app_data)

        if not app_data:
            app_data = ExtractSuite().get(app_name)
        
        installer(app_data)



    def uninstall_app(self, app_list):
        """Removes installed appimage and its files (.desktop...)."""
        installed_apps = self.installed_apps()
        for app in app_list:
            if app in installed_apps:
                self.file_suite.remove_app_files(installed_apps[app]['file_path'])
                print(f'App {installed_apps[app]} has been removed.')

    # Update function, checks update if there is update it will ask for update
    def uninstalled_update(self, files):
        """Update handler for not installed apps."""
        for file_ in files:
            if file_.endswith('.AppImage'):
                has_update = UpSuite().has_update(file_)

                if not has_update:
                    print(f'✅: {file_} is up to date.')
                    return

                choice  = input(f'New version founded for {file_}, upgrade? (Yn)').lower()
                if choice != 'y':
                    print('Bye')
                    return

                ## Update it
                has_update['app_cur_path'] = file_
                down_path = file_.split('/')
                del down_path[-1]
                down_path = "/".join(down_path)
                has_update['app_down_path'] = down_path
                has_update['app_cur_path'] = file_
                UpSuite().update_app(app_data=has_update)

def app_data_error_handler(app_data: dict, func) -> None:
    """Preventing code duplicate. Simple helper function for 
    outputing errors."""
    if app_data.get('Error'):
        print(app_data['Error'])
    else:
        func(app_data)


def main():
    """Entry point of cli app."""

    # Try for keyboard breaks.
    try:
        # Validators for parser
        def is_dir(path):
            """Check is path belongs to directory."""
            if os.path.isdir(path):
                return path
            raise argparse.ArgumentTypeError(f"readable_dir:{path} is not a valid path")

        def is_file(path):
            """Check is path belongs to file."""
            if os.path.isfile(path):
                return path
            raise argparse.ArgumentTypeError(f"readable_file:{path} is not exist")

        def is_valid_url_raise(url):
            """Raised version of is_valid_url"""
            if is_valid_url(url):
                return url
            raise argparse.ArgumentTypeError(f"url:{url} is not valid.")

        def is_installed(app_name):
            """If app is installed than raise."""
            if app_name in Aptod().installed_apps():
                return app_name
            raise argparse.ArgumentTypeError(
                f"App:{app_name} is not installed, it can't be remove."
            )

        parser = argparse.ArgumentParser(
            prog="Aptod",
            description="Install and update AppImages",
            formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=27))
        parser.add_argument('-V', '--version', action='version', version=f"Aptod ({__version__})")

        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            '--install', '-i',
            metavar='AppImage',
            help='Installs given AppImages.',
            nargs='*')
        group.add_argument(
            '--download', '-d',
            metavar='AppImage',
            help='Downloads given AppImages.',
            nargs='*')
        group.add_argument(
            '--update', '-u',
            metavar='AppImage',
            help='Updates, checks updates for given AppImage names.',
            nargs='*')
        group.add_argument(
            '--installed-apps', '-ia',
            help='Lists installed AppImages.',
            action='store_true')
        group.add_argument(
            '--available-apps', '-aa',
            help='Lists installable/downloadable AppImage names.',
            action='store_true')
        group.add_argument(
            '--add-repo', '-ar',
            help='Add new url repo.',
            type=is_valid_url_raise)
        group.add_argument(
            '--remove', '-rm',
            metavar='AppImage',
            nargs='*',
            help='Remove the installed app.',
            type=is_installed)       

        parser.add_argument(
            '--path', "-P",
            metavar='Path',
            help='If path is given, Aptod downloads AppImage files to given path.',
            type=is_dir)
        parser.add_argument(
            '--file', "-F",
            metavar='File',
            help='AppImage file full path\'s for the update.',
            type=is_file)
        parser.add_argument(
            '--show-unofficial', '-su',
            help='Show apps from unofficial repos.',
            action='store_true')     

        args = parser.parse_args()

        if args.add_repo:
            if len(args.add_repo) > 0:
                app_data = ExtractSuite().get(args.add_repo)
                app_data_error_handler(app_data, Aptod().file_suite.update_repo)

        if args.show_unofficial:
            select_menu = show_categories_menu
        else:
            select_menu = download_menu

        ## Read for -> isintance(args.foo, foo)
        # If args.foo is list, it means --foo entered by user
        # Otherwise it becomes None.

        # Install --install, -i
        if isinstance(args.install, list):
            app_list = args.install
            if not app_list:
                app_list = select_menu()
            
            for app in app_list:
                # If its dict than its from show_categories_menu
                if isinstance(app, dict):
                    app = app['url']
                Aptod().install_app(app)
                
        # List --installed-apps, -ia
        elif args.installed_apps:
            print('MY APPS:')
            app_list = list(Aptod().installed_apps().keys())
            for app in app_list:
                print(f'{app_list.index(app) + 1}){app}')

        # Download --download, -d
        elif isinstance(args.download, list):

            down_path = args.path
            if not down_path:
                down_path = os.getcwd()
            
            app_list = args.download
            if not app_list: 
                app_list = select_menu()

            for app in app_list:
                # If its dict than its from show_categories_menu
                if isinstance(app, dict):
                    app = app['url']
                app_data = ExtractSuite().get(app)
                app_data['app_down_path'] = down_path
                app_data_error_handler(app_data, downloader)

        # --update, -u
        elif isinstance(args.update, list):
            if len(args.update) > 0:
                Aptod().update_apps(app_list=args.update, operation='update')
            elif args.file:
                Aptod().uninstalled_update(args.file)
            else:
                # Check updates
                Aptod().update_apps(operation='update')

        # --avaliable-apps, -aa
        elif args.available_apps:
            print('AVAILABLE APPIMAGES:')
            for app in APP_LIST:
                print(f'{APP_LIST.index(app) + 1}){app}')

        # --remove -rm
        elif isinstance(args.remove, list):
            if len(args.remove) > 0:
                Aptod().uninstall_app(args.remove)
            elif Aptod().installed_apps():
                Aptod().uninstall_app(remove_menu())
            else:
                print('Curretly you don\'t have any installed app.')
     
        else:
            parser.print_help()

    except KeyboardInterrupt:
        print('Keyboard interrupt, exiting.')
