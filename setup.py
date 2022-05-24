#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import find_packages, setup

with open("README.md") as readme_file:
    readme = readme_file.read()

test_requirements = [
    "black>=19.10b0",
    "flake8>=3.8.3",
    "flake8-debugger>=3.2.1",
]

dev_requirements = [
    *test_requirements,
    "bump2version>=1.0.1",
    "ipython>=7.15.0",
    "m2r2>=0.2.7",
    "Sphinx>=3.4.3",
    "sphinx_rtd_theme>=0.5.1",
    "tox>=3.15.2",
    "twine>=3.1.1",
    "wheel>=0.34.2",
]

requirements = [
    "cdp-backend~=3.0",
    "requests~=2.25",
    "beautifulsoup4>=4.9",
    "pytz>=2021.1",
]

extra_requirements = {
    "test": test_requirements,
    "dev": dev_requirements,
    "all": [
        *requirements,
        *dev_requirements,
    ],
}

setup(
    author="Jackson Maxfield Brown, Sung Cho",
    author_email="jmaxfieldbrown@gmail.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    description="Scratchpad for scraper development and general utilities.",
    entry_points={
        "console_scripts": [],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=readme,
    long_description_content_type="text/markdown",
    include_package_data=True,
    keywords="cdp-scrapers",
    name="cdp-scrapers",
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*"]),
    python_requires=">=3.7",
    tests_require=test_requirements,
    extras_require=extra_requirements,
    url="https://github.com/CouncilDataProject/cdp-scrapers",
    # Do not edit this string manually, always use bumpversion
    # Details in CONTRIBUTING.rst
    version="0.4.0",
    zip_safe=False,
)
