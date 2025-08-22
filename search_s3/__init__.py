"""
S3 Object Search Tool

A powerful Python tool for searching S3 objects across multiple buckets with flexible filtering and output options.
"""

from .core import main, parse_arguments, format_size, compile_pattern, matches_pattern

__version__ = "1.0.0"
__author__ = "Alex van Rossum"
__email__ = "alexvanrossum@gmail.com"

__all__ = [
    "main",
    "parse_arguments", 
    "format_size",
    "compile_pattern",
    "matches_pattern",
    "__version__",
    "__author__",
    "__email__"
]
