from setuptools import setup, find_packages


setup(
    packages=find_packages(),
    install_requires=[
        'urwid>=2.0.0',
        'additional-urwid-widgets==0.4.1',
        'pyperclip>=1.7.0'
    ]
)
