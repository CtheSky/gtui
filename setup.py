import os
from setuptools import setup, find_packages

# read requirement.txt
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'requirements.txt')) as f:
    requirements = [_.strip() for _ in f.readlines() if not _.startswith('#')]

setup(
    install_requires=requirements,
    packages=find_packages()
)
