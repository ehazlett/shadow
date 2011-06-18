#!/usr/bin/env python

from distutils.core import setup

setup(name='shadow',
    version = '0.1',
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
    #install_requires = ['httplib2','paramiko'],
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

