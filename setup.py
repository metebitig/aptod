from setuptools import setup


VERSION = '0.0.1'
DESCRIPTION = 'Simple Cli App For Downloading AppImage\'s.'
LONG_DESC = 'Lorem ispum dolar sit amet.'


# Setting up
setup(
    name="aptod",
    packages=["aptod"],
    entry_points={
        "console_scripts": ['aptod = aptod.aptod:main']
        },
    version=VERSION,
    install_requires=[
        'beautifulsoup4>=4.11.1',
        'clint>=0.5.1',
        'requests>=2.4',
        'simple_term_menu>=1.6.0'
    ],
    description="Python command line application Aptod.",
    long_description=LONG_DESC,
    author="Mete",
    author_email="metebtg@protonmail.com",)
