#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import os
import sys
from shutil import rmtree

from setuptools import find_packages, setup, Command

# Package meta-data.
NAME = 'wccia'
DESCRIPTION = 'Tools for smart quotation generation.'
URL = 'https://github.com/gunterhf/wccia'
EMAIL = 'gunterh@weg.net'
AUTHOR = 'Günter Heinrich Herweg Filho'

# What packages are required for this module to be executed?
REQUIRED = [
    # 'requests', 'maya', 'records',
]

# The rest you shouldn't have to touch too much :)
# ------------------------------------------------
# Except, perhaps the License and Trove Classifiers!
# If you do change the License, remember to change the Trove Classifier for that!

here = os.path.abspath(os.path.dirname(__file__))



# Where the magic happens:
setup(
    name=NAME,
    #version=about['__version__'],
    description=DESCRIPTION,
    # long_description=long_description,
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    packages=find_packages(exclude=('tests',)),
    # If your package is a single module, use this instead of 'packages':
    # py_modules=['mypackage'],

    # entry_points={
    #     'console_scripts': ['mycli=mymodule:cli'],
    # },
    install_requires = [
        'nltk==3.4.1',
        'setuptools==65.5.1',
        #'sphinx==1.6.3',
        #'sphinx_rtd_theme==0.2.4',
        #'sphinx-argparse==0.2.1',
        'extract_msg==0.23.1',
        'EbookLib==0.16',
        'six==1.10.0',
        'pocketsphinx',
        'textract',
        'IMAPClient==2.1.0',
        'numpy==1.16.3',
        'PyPDF3==1.0.1',
        'beautifulsoup4==4.5.3',
        'pymongo==3.8.0',
        'scikit_learn==0.21.1',
        'stop-words',
        'minio'
    ],
    include_package_data=True,
    license='MIT',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ],

)
