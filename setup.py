from setuptools import setup, find_packages

setup(
    name="semantic_bibtool",
    version="0.2.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": ["semantic_bibtool = semantic_bibtool:main"]
    },
)
