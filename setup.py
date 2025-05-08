from setuptools import setup, find_packages

setup(
    name="cabcab",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click",
    ],
    entry_points={
        "console_scripts": [
            "cabcab=app.cli:main",
        ],
    },
)