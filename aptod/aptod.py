import os
import re
import argparse
from simple_term_menu import TerminalMenu

from .extract_suite import ExtractSuite
from .down_suite import DownSuite
from .up_suite import UpSuite
from .file_suite import FileSuite


__version__ = "0.0.1"


APP_LIST =  ExtractSuite().get('all')

def app_data_error_handler(func):    
    def wrapper():
        if app_data.get('Error'):
            print(app_data['Error'])
        else:
            func()    
    return wrapper

def download_menu():
    terminal_menu = TerminalMenu(
        APP_LIST,
        multi_select=True,
        show_multi_select_hint=True,
        menu_cursor_style=("fg_green", "bold"),
        title='Select for download:',
    )
    menu_entry_indices = terminal_menu.show()

    return list(terminal_menu.chosen_menu_entries) 

def remove_menu():
    terminal_menu = TerminalMenu(
        Aptod().installed_apps(),
        multi_select=True,
        show_multi_select_hint=True,
        menu_cursor_style=("fg_green", "bold"),
        title='Select for REMOVE:',
    )
    menu_entry_indices = terminal_menu.show()

    return list(terminal_menu.chosen_menu_entries) 


class Aptod:
    def __init__(self):
        self.fs = FileSuite()
        self.up = UpSuite()
        self.apps = APP_LIST        
        self.ds = DownSuite()

        data = self.fs.get_config()
        if not data:            
            self.fs.create_config()
            data = self.fs.get_config()
        self.main_folder = data['MainFolder']      

    def install_aptod(self):
        # If config file exists, app is intalled.
        if self.fs.get_config():
            print('Aptod is already installed.')
            return        
        self.fs.create_config()
    
    def create_repo(self):
        self.fs.create_repo()

    def installed_apps(self):
        """Returns installed app names as list."""

        # Get all appimage names in MainFolder
        installed_appimages = {}        
        apps_folder = self.fs.get_main_app_dir() 

        # If not appImage folder exist we will consider there is no app to update
        if not os.path.exists(apps_folder):
            return []
          
        for dir_ in os.listdir(apps_folder):
            # Requried for errors
            if not os.path.isfile(dir_):
                for file in os.listdir(apps_folder + '/' + dir_):                    
                    if file.lower().endswith('.appimage'):
                        installed_appimages[file] = apps_folder + '/' + dir_ + '/' + file
                        break
        
        # Convert appimage names to simple app name
        # Exmp. tutanota-desktop-linux-3-106-5.appimage > tutanota
        # And create dictionary with three data, file_name, name, file_path
        installed_apps = {}

        for file_name, file_path in installed_appimages.items(): 
            
            for app in self.apps:                  
                if app.lower() in file_name.lower() or app.lower().replace('-', '') in file_name.lower():
                    installed_apps[app] = {
                        'file_name': file_name,
                        'file_path': file_path,                        
                    }
                    break 
        return installed_apps

    def update_apps(self, **kwargs):
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
            app_data = self.up.has_update(app_path)
            # If functions returns data, there is a update
            if app_data.get('Error'):
                print(app_data['Error'])
            elif app_data:
                print(f'❌ {app} is old to date.')
                if kwargs.get('operation') == 'update':                
                    app_data['app_down_path'] = app_path.replace(app_name, '')
                    app_data['app_cur_path'] = app_path
                    self.up.update_app(app_data)
                    self.fs.create_desktop(app_data)
            else:
                print(f'✅ {app} is up to date.')  
    
    def install_app(self, app_list):
        if 'all' in app_list:
            app_list = ExtractSuite().get('all')
        for app in app_list:
            app_data = ExtractSuite().get(app)  
            if isinstance(app_data, dict) and app_data.get('Error'):
                print(app_data['Error']) 
            elif app_data:
                # Create folder with app name
                # Make first letter capital
                app = ''.join(re.findall('\w+', app_data['name'])[:2])
                down_path = self.main_folder + '/' + app
                if not os.path.exists(down_path):
                    os.makedirs(down_path)
                app_data['app_down_path'] = down_path
                self.ds.download(app_data)   
                # Create .desktop for integration
                self.fs.create_desktop(app_data)  
            else:
                print(app_data)

            
    
    def uninstall_app(self, app_list):
        installed_apps = self.installed_apps()
        for app in app_list:
            if app in installed_apps:
                self.fs.remove_app_files(installed_apps[app]['file_path'])
                print(f'App {installed_apps[app]} has been removed.')

    # Update function, checks update if there is update it will ask for update
    def uninstalled_update(self, files):
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
    if app_data.get('Error'):
        print(app_data['Error'])
    else:
        func(app_data)

# Entry point to cli             
def main():
    # Get avaliable app list    
    try:
        # Validators for parser
        def is_dir(path): 
            if os.path.isdir(path):
                return path        
            raise argparse.ArgumentTypeError(f"readable_dir:{path} is not a valid path")

        def is_file(path):        
            if os.path.isfile(path):
                return path        
            raise argparse.ArgumentTypeError(f"readable_file:{path} is not exist")  

        def is_valid_url(url):
            github_pattern = r'(https?:\/\/)*(www\.)*github\.com\/[a-zA-Z_0-9-]+\/[a-zA-Z_0-9-]+'
            # gitlab_pattern = r'(https?:\/\/)*(www\.)*gitlab\.com\/[a-zA-Z_]+'

            for pattern in [github_pattern]:
                if re.search(pattern, url):
                    return url
            raise argparse.ArgumentTypeError(f"url:{url} is not valid.") 
        
        def is_installed(app_name):
            if app_name in Aptod().installed_apps():
                return app_name 
            raise argparse.ArgumentTypeError(f"App:{app_name} is not installed, it can't be remove.") 

        parser = argparse.ArgumentParser(
            prog="Aptod",
            description="Install and update AppImage's",
            formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=27))   
        parser.add_argument('-V', '--version', action='version', version=f"Aptod ({__version__})")   

        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            '--install', '-i', 
            metavar='AppImage', 
            help='Installs given AppImage\'s.',            
            nargs='*')
        group.add_argument(
            '--download', '-d', 
            metavar='AppImage',
            help='Downloads given AppImage\'s.',              
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
            type=is_valid_url)
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

        args = parser.parse_args()

        if args.add_repo:
            if len(args.add_repo) > 0:
                app_data = ExtractSuite().get(args.add_repo)
                app_data_error_handler(app_data, Aptod().fs.update_repo)
                         
             

        # Install --install, -i
        if type(args.install) == list:
            if len(args.install) > 0:
                Aptod().install_app(args.install)            
            else:
                Aptod().install_app(download_menu())        
        # List --installed-apps, -ia
        elif args.installed_apps:
            print('MY APPS:')
            app_list = list(Aptod().installed_apps().keys())
            for app in app_list:
                print(f'{app_list.index(app) + 1}){app}')

        # Download --download, -d
        elif type(args.download) == list:                    
            if args.path:
                if len(args.download) > 0:
                    for app in args.download:
                        app_data = ExtractSuite().get(app)
                        app_data['app_down_path'] = args.path
                        app_data_error_handler(app_data, DownSuite().download)
                        # downloader_error_wrapper(app_data)
                        
                else:
                    for app in download_menu():
                        app_data = ExtractSuite().get(app)
                        app_data['app_down_path'] = args.path
                        app_data_error_handler(app_data, DownSuite().download)
            else:
                if len(args.download) > 0:
                    for app in args.download:
                        app_data = ExtractSuite().get(app)     
                        app_data['app_down_path'] = os.getcwd()
                        app_data_error_handler(app_data, DownSuite().download)
                else:
                    for app in download_menu():
                        app_data = ExtractSuite().get(app)
                        app_data['app_down_path'] = os.getcwd()
                        app_data_error_handler(app_data, DownSuite().download)
 
        
        # --update, -u
        elif type(args.update) == list:
            if len(args.update) > 0:
                Aptod().update_apps(app_list=args.update, operation='update')
            elif args.file:
                Aptod().uninstalled_update(args.file)
            else:
                # Check updates
                Aptod().update_apps(operation='update')

        # --avaliable-apps, -aa
        elif args.available_apps:
            print('AVAILABLE APPIMAGE\'S:')
            for app in APP_LIST:
                print(f'{APP_LIST.index(app) + 1}){app}')  

        elif type(args.remove) == list:   
            if len(args.remove) > 0:
                Aptod().uninstall_app(args.remove)           
            elif Aptod().installed_apps():
                Aptod().uninstall_app(remove_menu()) 
            else:
                print('Curretly you don\'t have any installed app.')   

    except KeyboardInterrupt:
        print('Keyboard interrupt, exiting.')
