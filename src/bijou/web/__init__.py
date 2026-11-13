"""Bijou web interface package and optional in-process desktop bridge."""

from bijou.web.bridge import BijouDesktopBridge
from bijou.web.desktop import launch_desktop

__all__ = ["BijouDesktopBridge", "launch_desktop"]
