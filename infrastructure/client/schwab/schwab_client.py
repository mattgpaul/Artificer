import os
import requests
import base64
import urllib.parse
import webbrowser
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from component.software.finance.timescale_enum import Timescale
from infrastructure.client.client import Client
from infrastructure.logging.logger import get_logger

class SchwabClient(Client):
    def __init__(self):
        self.api_key = os.getenv("SCHWAB_API_KEY")
        self.secret = os.getenv("SCHWAB_SECRET")
        self.app_name = os.getenv("SCHWAB_APP_NAME")
        self.logger = get_logger(self.__class__.__name__)

    @property
    def _app_authentication(self) -> None:
        pass

    def refresh_token(self) -> None:
        pass