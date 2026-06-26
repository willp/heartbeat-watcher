"""Heartbeat watcher daemon for evaluating heartbeat API state."""

from importlib.metadata import PackageNotFoundError, version

from .watcher import CONFIG_DIR_NAME, CONFIG_FILE_NAME, HbWatcher, main

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = [
    "CONFIG_DIR_NAME",
    "CONFIG_FILE_NAME",
    "HbWatcher",
    "__version__",
    "main",
]
