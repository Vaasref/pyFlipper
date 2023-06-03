class SerialException(Exception):
    """Absctraction for all serial exceptions"""
    pass

class NoFlipperFound(SerialException):
    """Raised when no Flipper Zero is found"""
    pass



class FlipperException(Exception):
    """Absctraction for all Flipper exceptions
    
    Pure use may indicate incompatibility with Flipper Zero"""
    pass

class FlipperError(FlipperException):
    """Raised when Flipper returns an error message"""
    pass

class FlipperTimeout(FlipperException):
    """Raised when Flipper does not respond in time"""
    pass


# Storage exceptions

class StorageException(FlipperException):
    """Absctraction for all storage exceptions"""
    pass

class StoragePathInvalid(StorageException):
    """Raised when path is invalid"""
    pass

class StorageMD5Mismatch(StorageException):
    """Raised when MD5 checksum doesn't match"""
    pass

class StoragePathNotFile(StorageException):
    """Raised when path is not a file"""
    pass

class StoragePathNotDir(StorageException):
    """Raised when path is not a directory"""
    pass

class StoragePathNotFree(StorageException):
    """Raised when path is not free"""
    pass

class StoragePathFree(StorageException):
    """Raised when path is free"""
    pass