#!/usr/bin/env python

from distutils.core import setup
import sys

if sys.version_info < (2,7):
    REQUIRES = ['argparse']
else:
    REQUIRES = []

setup(name='shadow',
    version = '0.34',
    author = 'Evan Hazlett',
    author_email = 'ejhazlett@gmail.com',
    packages = ['shadow'],
    description = 'btrfs snapshot utility',
    url = 'http://github.com/ehazlett/shadow',
    license = 'License :: OSI Approved :: GNU General Public License (GPL)',
    long_description = """
    Shadow is a snapshot management utility for btrfs
    """,
    download_url = 'https://github.com/ehazlett/shadow/tarball/master',
    scripts = ['shadowconsole'],
    install_requires = REQUIRES,
    platforms = [
        "All",
        ],
    classifiers = [
        "Programming Language :: Python",
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Topic :: Utilities",
        ]
    )

