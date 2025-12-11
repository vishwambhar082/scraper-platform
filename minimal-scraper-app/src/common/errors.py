class ScraperError(Exception):
    pass

class LoginError(ScraperError):
    pass

class BlockedError(ScraperError):
    pass

class CircuitOpenError(ScraperError):
    pass
