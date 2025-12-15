"""
Stealth Engine Module

Advanced stealth browsing capabilities to avoid bot detection.

Implements multiple anti-detection techniques:
- User agent rotation
- Header randomization
- Fingerprint masking
- WebDriver property hiding
- Canvas fingerprinting protection
- WebRTC leak prevention

Author: Scraper Platform Team
"""

import logging
import random
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class StealthEngine:
    """
    Advanced stealth browsing engine with comprehensive anti-detection.

    Features:
    - Realistic user agent rotation
    - Browser fingerprint randomization
    - WebDriver property hiding
    - Canvas and WebGL fingerprint protection
    - WebRTC leak prevention
    - Timezone and locale spoofing
    """

    # Realistic user agent strings (2023-2025)
    USER_AGENTS = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",

        # Chrome on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",

        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",

        # Firefox on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",

        # Safari on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",

        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]

    # Accept-Language variations
    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "en-GB,en;q=0.9",
        "en-US,en;q=0.9,es;q=0.8",
        "en-CA,en;q=0.9",
    ]

    # Accept-Encoding
    ACCEPT_ENCODINGS = [
        "gzip, deflate, br",
        "gzip, deflate",
    ]

    # Common screen resolutions
    SCREEN_RESOLUTIONS = [
        (1920, 1080),
        (1366, 768),
        (1440, 900),
        (1536, 864),
        (2560, 1440),
        (1680, 1050),
    ]

    # Timezone offsets (minutes)
    TIMEZONES = [
        -480,  # PST
        -300,  # EST
        0,     # GMT
        60,    # CET
        120,   # EET
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize stealth engine.

        Args:
            config: Optional configuration dict
        """
        self.config = config or {}
        self._current_profile = self._generate_browser_profile()
        logger.info("Initialized StealthEngine with advanced anti-detection")

    def _generate_browser_profile(self) -> Dict[str, Any]:
        """Generate a consistent browser fingerprint profile."""
        width, height = random.choice(self.SCREEN_RESOLUTIONS)

        profile = {
            "user_agent": random.choice(self.USER_AGENTS),
            "accept_language": random.choice(self.ACCEPT_LANGUAGES),
            "accept_encoding": random.choice(self.ACCEPT_ENCODINGS),
            "viewport": {
                "width": width,
                "height": height
            },
            "screen": {
                "width": width,
                "height": height,
                "colorDepth": 24,
                "pixelDepth": 24
            },
            "timezone_offset": random.choice(self.TIMEZONES),
            "platform": self._get_platform_from_ua(random.choice(self.USER_AGENTS)),
            "hardware_concurrency": random.choice([2, 4, 8, 12, 16]),
            "device_memory": random.choice([4, 8, 16]),
            "max_touch_points": 0,
        }

        logger.debug(f"Generated browser profile: {profile['user_agent'][:50]}...")
        return profile

    def _get_platform_from_ua(self, user_agent: str) -> str:
        """Extract platform from user agent string."""
        if "Windows" in user_agent:
            return "Win32"
        elif "Macintosh" in user_agent or "Mac OS" in user_agent:
            return "MacIntel"
        elif "Linux" in user_agent:
            return "Linux x86_64"
        return "Unknown"

    def get_stealth_headers(self) -> Dict[str, str]:
        """
        Get randomized stealth headers.

        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "User-Agent": self._current_profile["user_agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": self._current_profile["accept_language"],
            "Accept-Encoding": self._current_profile["accept_encoding"],
            "DNT": "1",  # Do Not Track
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

        # Add Chrome-specific headers if Chrome UA
        if "Chrome" in self._current_profile["user_agent"]:
            headers["sec-ch-ua"] = '"Not_A Brand";v="8", "Chromium";v="120"'
            headers["sec-ch-ua-mobile"] = "?0"
            headers["sec-ch-ua-platform"] = f'"{self._current_profile["platform"]}"'

        return headers

    def apply_stealth(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply stealth settings to configuration.

        Args:
            config: Engine configuration

        Returns:
            Updated configuration with stealth settings
        """
        config = config.copy()

        # Apply headers
        if "headers" not in config:
            config["headers"] = {}
        config["headers"].update(self.get_stealth_headers())

        # Apply viewport settings (for browser engines)
        config["viewport"] = self._current_profile["viewport"]

        # Add stealth scripts injection settings
        config["stealth_scripts"] = {
            "hide_webdriver": True,
            "mask_canvas": True,
            "mask_webgl": True,
            "prevent_webrtc_leak": True,
            "spoof_timezone": True,
            "timezone_offset": self._current_profile["timezone_offset"],
        }

        # Browser-specific settings
        config["browser_args"] = self._get_browser_args()

        logger.debug("Applied stealth configuration")
        return config

    def _get_browser_args(self) -> List[str]:
        """Get browser launch arguments for stealth."""
        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",  # Consider security implications
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-position=0,0",
            "--ignore-certificate-errors",
            "--ignore-certificate-errors-spki-list",
            "--disable-web-security",  # Use with caution
            f"--window-size={self._current_profile['viewport']['width']},{self._current_profile['viewport']['height']}",
        ]
        return args

    def get_stealth_scripts(self) -> List[str]:
        """
        Get JavaScript snippets to inject for stealth.

        Returns:
            List of JavaScript code strings
        """
        scripts = []

        # Hide WebDriver property
        scripts.append("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Override navigator properties
        scripts.append(f"""
            Object.defineProperty(navigator, 'platform', {{
                get: () => '{self._current_profile["platform"]}'
            }});

            Object.defineProperty(navigator, 'hardwareConcurrency', {{
                get: () => {self._current_profile["hardware_concurrency"]}
            }});

            Object.defineProperty(navigator, 'deviceMemory', {{
                get: () => {self._current_profile["device_memory"]}
            }});

            Object.defineProperty(navigator, 'maxTouchPoints', {{
                get: () => {self._current_profile["max_touch_points"]}
            }});
        """)

        # Canvas fingerprinting protection
        scripts.append("""
            const originalGetContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type, ...args) {
                const context = originalGetContext.apply(this, [type, ...args]);
                if (type === '2d') {
                    const originalGetImageData = context.getImageData;
                    context.getImageData = function(...args) {
                        const imageData = originalGetImageData.apply(this, args);
                        // Add minimal noise to canvas
                        for (let i = 0; i < imageData.data.length; i += 4) {
                            imageData.data[i] += Math.floor(Math.random() * 3) - 1;
                        }
                        return imageData;
                    };
                }
                return context;
            };
        """)

        # WebGL fingerprinting protection
        scripts.append("""
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
                    return 'Intel Inc.';
                }
                if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter.apply(this, [parameter]);
            };
        """)

        # WebRTC leak prevention
        scripts.append("""
            if (window.RTCPeerConnection) {
                window.RTCPeerConnection = new Proxy(window.RTCPeerConnection, {
                    construct(target, args) {
                        const config = args[0] || {};
                        config.iceServers = [];
                        return new target(config);
                    }
                });
            }
        """)

        # Chrome detection evasion
        scripts.append("""
            if (!window.chrome) {
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {}
                };
            }

            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)

        # Timezone spoofing
        timezone_offset = self._current_profile["timezone_offset"]
        scripts.append(f"""
            Date.prototype.getTimezoneOffset = function() {{
                return {timezone_offset};
            }};
        """)

        return scripts

    def inject_stealth_scripts(self, page: Any) -> None:
        """
        Inject stealth scripts into a page (for Playwright/Selenium).

        Args:
            page: Page object (Playwright Page or Selenium WebDriver)
        """
        scripts = self.get_stealth_scripts()

        for script in scripts:
            try:
                # Try Playwright API
                if hasattr(page, 'add_init_script'):
                    page.add_init_script(script)
                # Try Selenium API
                elif hasattr(page, 'execute_cdp_cmd'):
                    page.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                        'source': script
                    })
                # Try direct execute_script
                elif hasattr(page, 'execute_script'):
                    page.execute_script(script)

            except Exception as e:
                logger.warning(f"Failed to inject stealth script: {e}")

    def rotate_profile(self) -> None:
        """Generate a new browser profile (rotate fingerprint)."""
        self._current_profile = self._generate_browser_profile()
        logger.info("Rotated browser profile")

    def get_current_profile(self) -> Dict[str, Any]:
        """
        Get current browser profile.

        Returns:
            Current profile dictionary
        """
        return self._current_profile.copy()


def create_stealth_engine(config: Optional[Dict[str, Any]] = None) -> StealthEngine:
    """
    Factory function to create a stealth engine.

    Args:
        config: Optional configuration

    Returns:
        StealthEngine instance
    """
    return StealthEngine(config=config)


__all__ = ["StealthEngine", "create_stealth_engine"]
