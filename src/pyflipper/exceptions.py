class SerialException(Exception):
    """Absctraction for all serial exceptions"""
    pass



class FlipperException(Exception):
    pass

class FlipperError(FlipperException):
    """Raised when Flipper returns an error message"""
    pass

class FlipperTimeout(FlipperException):
    """Raised when Flipper does not respond in time"""
    pass