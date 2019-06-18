from setuptools import setup, find_packages
from cwl_helper.constants import __program__, __version__

# Temporary workaround for cwlgen failing to install:
# pip install ruamel.yaml==0.13.13 git+https://github.com/common-workflow-language/python-cwlgen.git

setup(
    name=__program__,
    version=__version__,
    author="mattdoug604",
    author_email="mattdoug604@gmail.com",
    packages=find_packages(),
    description="Automatically generate a bare-bones CWL tool for your program of interest.",
    url="https://github.com/mattdoug604/cwl-helper.git",
    python_requires=">=3",
    include_package_data=True,
    install_requires=["cwlgen"],
    entry_points={
        'console_scripts': ['cwl-helper = cwl_helper.main:main']
    },
)
