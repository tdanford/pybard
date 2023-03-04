#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="pybard",
    version="0.1.0",
    description="",
    url="https://www.github.com/tdanford/pybard",
    packages=find_packages(),
    entry_points = {
        "console_scripts": [
            "bard=bard.cli:main"
        ]
    },
    install_requires=[
        "requests", 
        "click", 
        "rich"
    ],
    tests_require=[
        "pytest", 
        "black", 
        "pytest-black", 
        "pytest-cov",
        "hypothesis"
    ],
)
