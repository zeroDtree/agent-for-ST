"""
Interfaces package - Provides clean interfaces for breaking circular dependencies
"""

from .web_interface import WebConfirmationInterface, web_confirmation_interface

__all__ = [
    "web_confirmation_interface",
    "WebConfirmationInterface",
]
