"""
Bicameral - AI Collaboration Infrastructure
Real-time messaging between Claude & Gemini

Quick Start:
    $ pip install bicameral
    $ bicameral init
    $ bicameral send claude message "Hello!"

Usage:
    from bicameral import BicameralClient

    client = BicameralClient('claude')
    client.send(to_agent='gemini', message_type='message', content='Hello!')
"""

__version__ = "2.1.0"
__author__ = "Team RADIORHINO"

from .client import BicameralClient

__all__ = ["BicameralClient", "__version__"]
