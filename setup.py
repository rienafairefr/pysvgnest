#! /usr/bin/env python
# -*- coding:utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='svgnest',
    version='0.1',
    description='SVG nesting',
    author='Matthieu Berthomé',
    author_email='matthieu.berthome@gmail.com',
    url='',
    license='MIT',
    download_url='http://github.com/rienafairefr/pysvgnest/',
    packages=find_packages(),
    classifiers=['Development Status :: 4 - Beta',
                 'Programming Language :: Python',
                 'Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7'],
    install_requires=['lxml', 'svgwrite', 'rectpack', 'svgpathtools'],
    python_requires='>=2.7,',
)
