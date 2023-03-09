"""Top-level package for cdp_scrapers."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("cdp-scrapers")
except PackageNotFoundError:
    __version__ = "uninstalled"

__author__ = "Eva Maxfield Brown, Sung Cho, Shak Ragoler"
__email__ = "evamaxfieldbrown@gmail.com"
