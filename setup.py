from setuptools import setup, find_packages
import os

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="cabcab",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "cabcab=app.cli:main",
            "cabcab-server=server:cli",
        ],
    },
)