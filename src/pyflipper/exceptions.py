class SerialException(Exception):
    """Absctraction for all serial exceptions"""
    pass



class FlipperException(Exception):
    pass

class FlipperErrorException(Exception):
    """Raised when Flipper returns an error message"""
    pass

class FlipperTimeoutException(FlipperException):
    """Raised when Flipper does not respond in time"""
    pass