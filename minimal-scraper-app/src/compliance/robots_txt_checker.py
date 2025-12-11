"""
Robots.txt compliance helper.
"""
from __future__ import annotations

from functools import lru_cache
from urllib import robotparser
from urllib.parse import urlparse

import requests


class RobotsTxtChecker:
    def __init__(self, user_agent: str = "scraper-platform") -> None:
        self.user_agent = user_agent

    @staticmethod
    @lru_cache(maxsize=128)
    def _fetch_robots_txt(base_url: str) -> robotparser.RobotFileParser:
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        response = requests.get(robots_url, timeout=10)
        response.raise_for_status()
        parser = robotparser.RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        return parser

    def is_allowed(self, url: str) -> bool:
        parser = self._fetch_robots_txt(url)
        return parser.can_fetch(self.user_agent, url)

