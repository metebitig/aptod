import shutil 
import os
import json
import  re

from .logo_maker import logo_generator


"""
This class releated with file opertions.
It will create or delete config, dir... and that kind a things.
"""


class FileSuite:    
    def __init__(self):
        self.cfg_dir = os.path.expanduser('~') + "/.config/aptod" 
        self.cfg_pth = self.cfg_dir + '/aptod.conf'
        self.repo_pth = self.cfg_dir + '/aptod_repo.json'

    def create_config(self):

        if os.path.exists(self.cfg_pth):
            print(f'Config file aldready exist at "{self.cfg_pth}"')
            return

        # If also folder not exist create them.
        if not os.path.exists(self.cfg_dir):
            os.makedirs(self.cfg_dir)

        # Finally create .conf         
        cfg_data = {"MainFolder": f"{os.path.expanduser('~')}/appImage"}

        # Write first config
        with open(self.cfg_pth, 'w') as file:
            json.dump(cfg_data, file, indent = 2) 

        if not os.path.exists(cfg_data['MainFolder']):
            os.makedirs(cfg_data['MainFolder'])
        
    def create_repo(self):
        if os.path.exists(self.repo_pth):
            print(f'Repo file aldready exist at "{self.repo_pth}"')
            return   

        with open(self.repo_pth, 'w') as file:
            json.dump({}, file, indent = 2) 

    def update_repo(self, app_data: dict):
        """Adds new url to local repo file."""
        url = app_data['down_url']
        
        def app_name_generator(url):          

            list_of_url = url.split('.com/', 1)[1]
            repo_name = list_of_url.split('/')[1]
            
            # Capitalize each capital letter, than remove spaces in name
            app_name = ' '.join(re.findall('\w+', repo_name)).title().replace(" ", '') 

           # If app name not in in file name, change app name
           # Example: BraveAppImage is not in brave-stable.AppImage
           # In bellow we will assing app_name to brave-stable
            if not re.search(app_name, app_data['name'], re.IGNORECASE):                
                app_name_list = re.findall(r'[A-Za-z]+', app_data['name'])
                app_name = app_data['name'].split(app_name_list[1])[0] + app_name_list[1] 

            return app_name                
        
        app_name = app_name_generator(url)

        if not os.path.exists(self.repo_pth):
            self.create_repo()

        with open(self.repo_pth, "r") as data_file:
            # Reading old data
            data = json.load(data_file)

        data[app_name] = url
        with open(self.repo_pth, 'w') as file:
            json.dump(data, file, indent = 2) 

        return data

    def get_repo(self):
        if not os.path.exists(self.repo_pth):
            return {}

        with open(self.repo_pth, "r") as data_file:
            # Reading old data
            data = json.load(data_file)

        return data

    def get_main_app_dir(self) -> str:
        with open(self.cfg_pth) as file:
            data = json.load(file)
        
        return data['MainFolder']
    
    def get_config(self) -> dict:
        if not os.path.exists(self.cfg_pth):
            return {}        
        
        with open(self.cfg_pth, "r") as data_file:
            try:
                data = json.load(data_file)
            except json.decoder.JSONDecodeError:
                # If json is corrupted delete and create new one     
                os.remove(self.cfg_pth)
                self.create_config()
                with open(self.cfg_pth, "r") as data_file:
                    data = json.load(data_file)

        return data

    def find_app(self, directory: str, name: str) -> str:
        """ Returns first file path that ends with .appimage extension
        from given path's folder that includes name."""

        # Loop all folder names
        for dir_ in os.listdir(directory):
            # name(librewolf, tutanota...).
            if name.lower() in dir_.lower():
                # Than only focus returning .AppImage
                # For make this always work, after-
                #updating, old .AppImage should be deleted.
                for file_ in os.listdir(os.path.join(directory, dir_)):                    
                    if re.search(r'.AppImage$', file_, re.IGNORECASE):
                        return os.path.join(directory, dir_, file_)
        # raise FileNotFoundError(f'App is not exist in "{directory}"')
        return '' 
    
    def create_desktop(self, app_data):
        """Creates .desktop files but if they exist
        than only updates with new data."""
        
        app_full_path = os.path.join(app_data['app_down_path'], app_data['name']) 
        # Make .AppImage file exacutable
        os.system(f'chmod +x {app_full_path}')
        
        path = f'{os.path.expanduser("~")}/.local/share/applications/'
        if not os.path.exists(path):
            os.makedirs(path)

        app_name = re.findall('\w+', app_data['name'])[0].lower()
        desktop_path = path + app_name + '.desktop'
        app_icon_path = os.path.join(app_data['app_down_path'], "icon.png")

        if not os.path.exists(app_icon_path):                        
            with open(app_icon_path, 'wb') as file:            
                example_dot = file.write(logo_generator(re.findall('\w+', app_data['name'])[0]))

        # If .desktop is exist only change version
        if not os.path.exists(desktop_path):                   
            with open(f'{os.path.dirname(__file__)}/data/example.desktop', 'r') as file:            
                example_dot = file.read()
            
            example_dot = example_dot.replace('{app_path}', os.path.join(app_data['app_down_path'], app_data['name']))
            example_dot = example_dot.replace('{app_name}', re.findall('\w+', app_data['name'])[0])
            example_dot = example_dot.replace('{app_icon_path}', app_icon_path)

            with open(desktop_path, 'w') as file:
                file.write(example_dot)
        else:
            # If .dekstop exist than only update app name in .desktop
            with open(desktop_path, 'r') as file:
                desktop_f = file.read()
            # Get the will replaced item
            first_word = re.findall('\w+', app_data['name'])[0]            
            to_replace = re.search(f'{first_word}(.*).AppImage', desktop_f).group()
            # When sub dir name is same with app name, remove sub dir name
            if '/' in to_replace:
                to_replace = to_replace.split('/')[-1]
            desktop_f = desktop_f.replace(to_replace, app_data['name'])
            with open(desktop_path, 'w') as file:
                file.write(desktop_f)         

    def remove_app_files(self, path):
        desktop_sub_path = f'{os.path.expanduser("~")}/.local/share/applications/'  
        
        app_desktop_file = desktop_sub_path + re.findall('\w+', path.split('/')[-1])[0] + '.desktop'
        path = path.replace('/' + path.split('/')[-1], '')

        # Bellow could be dangerous if any bugs occur!
        # So good to have extra protection with if statment bellow
        if 'appImage' in path:
            shutil.rmtree(path)
            os.remove(app_desktop_file)
