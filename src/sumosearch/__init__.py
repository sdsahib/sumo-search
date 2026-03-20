from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("sumosearch")
except PackageNotFoundError:
    __version__ = "unknown"
