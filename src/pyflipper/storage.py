import re
import hashlib

import fnmatch
import posixpath
from functools import cached_property
from pathlib import PurePath, _Flavour
from urllib.parse import quote_from_bytes as urlquote_from_bytes

from pyflipper.serial import SerialFunction
from pyflipper.utils import parse_fs_size
from pyflipper.exceptions import FlipperException, FlipperError, StorageException, StoragePathNotFile, StoragePathNotDir, StoragePathInvalid, StoragePathNotFree, StoragePathFree


class _FlipperFlavour(_Flavour):
    sep = '/' 
    altsep = None
    has_drv = True
    pathmod = posixpath

    storages = set(['/ext', '/int'])

    def splitroot(self, part, sep=sep):
        if part and part[0] == sep:
            storage = part[:4]
            if storage in self.storages:
                if len(part) == 4:
                    return '', storage, '' # path is root
                return storage, sep, part[5:] # path is not root but still absolute
        return '', '', part
 
    def casefold(self, s):
        return s

    def casefold_parts(self, parts):
        return parts
    
    def compile_pattern(self, pattern):
        return re.compile(fnmatch.translate(pattern)).fullmatch

    def is_reserved(self, parts):
        return False

    def make_uri(self, path):
        bpath = bytes(path)
        return 'flipper://' + urlquote_from_bytes(bpath) # I have no idea of what I'm doing, but that looks fine
    

_flipper_flavour = _FlipperFlavour()

class PureFlipperPath(PurePath): # Next step is to implement the non-pure version
    _flavour = _flipper_flavour

    def __new__(cls, *args, **kwargs):
        path = super().__new__(cls, *args, **kwargs)
        if not path.is_absolute():
            raise StoragePathInvalid(f'Path {path} must start with "/ext or "/int"')
        return path

    def is_absolute(self):
        return self.parts[0].rstrip('/') in self._flavour.storages

    def is_internal(self):
        return self.parts[0] == '/int'
    
    def is_external(self):
        return self.parts[0] == '/ext'

    def is_root(self):
        return len(self.parts) == 1


class FlipperPath(PureFlipperPath):
    _flipper = None
    _serial_wrapper = None

    @classmethod
    def _from_parts(cls, flipper, *args):
        if flipper is None or flipper.__class__.__name__ != 'PyFlipper':
            raise ValueError("Flipper instance is required, if you see this error, please report it on and your use case")
        drv, root, parts = cls._parse_args(args)
        return cls._from_parsed_parts(flipper, drv, root, parts)

    @classmethod
    def _from_parsed_parts(cls, flipper, drv, root, parts):
        if flipper is None or flipper.__class__.__name__ != 'PyFlipper':
            raise ValueError("Flipper instance is required, if you see this error, please report it on and your use case")
        self = object.__new__(cls)
        self._drv = drv
        self._root = root
        self._parts = parts
        self._flipper = flipper
        self._serial_wrapper = flipper._serial_wrapper
        return self

    @cached_property
    def parent(self):
        drv, root, parts = self._parse_args(self.parts[:-1])
        return self._from_parsed_parts(self._flipper, drv, root, parts)

    @property
    def parents(self):
        for i in range(1, len(self.parts)):
            drv, root, parts = self._parse_args(self.parts[:-i])
            yield self._from_parsed_parts(self._flipper, drv, root, parts)

    def __new__(cls, *args, **kwargs):
        flipper = None
        if isinstance(args[0], FlipperPath):
            flipper = args[0]._flipper
            if len(args) > 1: 
                args = args[1:] # only remove passed FlippertPath if there are other args otherwise copy it (and allow to pass an other PyFlipper instance as keyword argument)
        elif args[0].__class__.__name__ == 'PyFlipper':
            flipper = args[0]
            args = args[1:]
        flipper = kwargs.pop('flipper', flipper) # flipper passed as keyword argument takes precedence

        if not flipper:
            raise StorageException("Flipper instance is required")
        
        path = cls._from_parts(flipper, *args)
        if not path.is_absolute():
            raise StoragePathInvalid(f'Path {path} must start with "/ext or "/int"')
        return path

    _stat = None
    @property
    def stat(self):
        if self._stat is None:
            try:
                self._stat = self._flipper.storage.stat(self)
            except StorageException as e:
                self._stat = {}
        return self._stat
    
    _tree = None
    @property
    def tree(self):
        if self._tree is None:
            if self.stat['type'] == 'dir' or self.stat['type'] == 'storage': # checking directly to pull full stat if needed
                self._tree = self.stat['tree']
            else:
                raise StoragePathNotDir(f"Path {self} is not a directory")
        return self._tree

    def exists(self):
        return self.type != ''
    
    def is_dir(self):
        return self.type == 'dir'
    
    def is_file(self):
        return self.type == 'file'
    
    def is_storage(self):
        return self.type == 'storage'

    def iterdir(self):
        if self.stat['type'] == 'dir' or self.stat['type'] == 'storage': # checking directly to pull full stat if needed
            for child in self.tree['children']:
                if child.parts[:len(self.parts)] == self.parts and len(child.parts) == len(self.parts) + 1:
                    yield FlipperPath(self._flipper, child['path'])
        else:
            raise StoragePathNotDir(f"Path {self} is not a directory")

    def mkdir(self, make_parents=False, exist_ok=False):
        if self.is_root():
            if exist_ok is False: # semantically close enough
                raise StoragePathInvalid('Path cannot be root ("/ext" or "/int")')
        elif self.is_file():
            raise StoragePathNotDir(f"Path {self} is already a file")
        elif self.is_dir():
            if exist_ok is False:
                raise StoragePathNotFree(f"Path {self} already exists")
        else:
            if make_parents:
                try:
                    self.parent.mkdir(make_parents=True, exist_ok=True)
                except StoragePathNotDir:
                    raise StoragePathInvalid(f"Path {self.parent} is not a directory or root")
            else:
                for parent in self.parents:
                    if parent.is_free():
                        raise StoragePathInvalid(f"Path {self} parent directory doesn't exist, use make_parents=True to create it")
                    if parent.is_file():
                        raise StoragePathInvalid(f"Path {parent} is not a directory or root")
            self._flipper.storage.mkdir(self)
    
    def remove(self, recursive=False, remove_contents=False):
        if recursive:
            if len(self.tree['files']) > 0:
                if remove_contents:
                    for file in self.tree['files']:
                        self._flipper.storage.remove(file['path'])
                else:
                    raise StorageException(f"Directory {self} (or its subdirectories) contains files, use remove_contents=True to remove them")
            #sort directories by decreasing depth to be able to remove them
            dirs = sorted(self.tree['dirs'], key=lambda x: len(x['path'].parts), reverse=True)
            for dir in dirs:
                self._flipper.storage.remove(dir['path'])
        else:
            list = self._flipper.storage._explorer('list', self)
            if len(list['files']) == 0:
                if len(list['dirs']) > 0:
                    raise StorageException(f"Directory {self} contains subdirectories, use recursive=True to remove them")
            else:
                if len(list['dirs']) > 0:
                    raise StorageException(f"Directory {self} contains subdirectories and files, use recursive=True and remove_contents=True to remove them")
                elif not remove_contents:
                    raise StorageException(f"Directory {self} contains files, use remove_contents=True to remove them")
                else:
                    for file in list['files']:
                        self._flipper.storage.remove(file['path'])
        self._flipper.storage.remove(self)
            
    def is_free(self):
        return self.exists() is False
    
    def is_not_free(self):
        return self.exists() is True

    def is_empty(self):
        if self.is_not_free():
            if self.is_file():
                return self.size == 0
            elif self.is_dir():
                return len(self._flipper.storage.list(self)['children']) == 0
            else:
                raise StoragePathInvalid(f"Path {self} is not a file or directory")    
        else:
            raise StoragePathFree(f"Path {self} doesn't exist")

    @cached_property
    def type(self):
        if self._stat is None:
            try:
                stat = self._flipper.storage.stat(self, extended=False)
                return stat['type']
            except StorageException as e: # for some reason until I tried to add "as e" it printed the exception instead of passing it
                pass
        else:
            return self.stat['type']
        return ""
    
    @property
    def size(self):
        if self.exists() is False:
            raise StoragePathFree(f"Path {self} doesn't exist")
        elif self.is_file():
            return self.stats['size']
        elif self.is_dir():
            return self.stats['total_size']
        elif self.is_storage():
            return self.stats['free_space']
        else:
            raise StoragePathInvalid(f"Path {self} is not a file, directory or storage")


class File(SerialFunction):
    def read(self, path:FlipperPath, check_md5:bool=True) -> dict:
        """
        Read file from Flipper Zero

        Args:
            path(FlipperPath): File path
            check_md5 (bool, optional)(default: True): If True, check MD5 checksum

        Returns:
            dict: File stats and data

        Raises:
            FlipperException: If couldn't read file or MD5 checksum mismatch
            StoragePathNotFile: If path is not a file
            StoragePathFree: If path doesn't exist
        """
        output = {}
        if isinstance(path, str) or isinstance(path, PureFlipperPath):
            path = FlipperPath(self._flipper, path)
        if path.is_not_free():
            if path.is_file():
                if check_md5:
                    output = path.stat
                else:
                    output['path'] = str(path)
                    output['type'] = 'file'
                output['data'] = self._flipper.storage.read(path)
                output['size'] = len(output['data']) # override stat size with actual data size
                if check_md5:
                    md5_checksum = hashlib.md5(output['data']).hexdigest()
                    if md5_checksum != output['md5']:
                        raise FlipperException(f"MD5 checksum mismatch for file {path} (expected: {output['md5']}, got: {md5_checksum})", output)
            else:
                raise StoragePathNotFile(f"Path {path} is not a file")
        else:
            raise StoragePathFree(f"Path {path} doesn't exist")
        return output


    def write(self, path:FlipperPath, data:bytes, overwrite:bool=True, create_parents:bool=False) -> None:
        """
        Write file to Flipper Zero

        Args:
            path (FlipperPath): File path
            data (bytes): File data
            overwrite (bool, optional)(default: True): If True, overwrite file if it already exists
            create_parents (bool, optional)(default: False): If True, create parent directories if they don't exist

        Raises:
            StoragePathNotFile: If path is not a file
            StoragePathNotFree: If path already exists and overwrite is False
            StoragePathInvalid: If path is invalid, either directly or because of its parent
        """
        if isinstance(path, str) or isinstance(path, PureFlipperPath):
            path = FlipperPath(self._flipper, path)
        if path.exists():
            if path.is_file():
                if not overwrite:
                    raise StoragePathNotFree(f"File {path} already exists, use overwrite=True to overwrite it")
            elif path.is_dir():
                raise StoragePathNotFile(f"Path {path} is a directory, not a file")
            else:
                raise StoragePathInvalid(f"Path {path} is not a file")
        if path.parent.is_file():
            raise StoragePathInvalid(f"Path {path.parent} is not a directory or root")
        if create_parents:
            path.parent.mkdir(make_parents=True, exist_ok=True)
        
        if isinstance(data, str):
            data = data.encode()
        data = data.replace(b'\r\n', b'\x0d')
        self._serial_wrapper.write(f"storage write {path}\r".encode())
        self._serial_wrapper.write(data)
        self._serial_wrapper.kill_cmd()



class Storage(SerialFunction):  
    def __init__(self, flipper=None) -> None:
        super().__init__(flipper)
        self.file = File()

    def info(self, path: str) -> dict:
        path = PureFlipperPath(path)
        if not path.is_root():
            raise StoragePathInvalid('Path must be root ("/ext" or "/int")')
        received = self._serial_wrapper.send(f"storage info {path}").strip("\r\n ")
        received = received.split("\r\n")
        if len(received) != 6:
            raise FlipperException("Couldn't load storage info")
        output = {}
        output['label'] = received[0].removeprefix("Label: ")
        output['fs_format'] = received[1].removeprefix("Type: ")
        output['total_size'] = parse_fs_size(received[2].removesuffix(" total"))
        output['free_space'] = parse_fs_size(received[3].removesuffix(" free"))
        output['model'] = received[4].strip()
        output['sn'] = received[5].removeprefix("SN:").strip()
        return output
        
    def format(self):
        raise NotImplementedError("Format is not implemented yet")

    def _explorer(self, cmd: str, path: str) -> dict:
        children_p = re.compile("\[([FD])\]\s([^\s]+)(?:\s(\d+\w+))?\r\n")
        path = PureFlipperPath(path)
        received = self._serial_wrapper.send(f"storage {cmd} {path}")
        children = []
        dirs = []
        files = []
        for c in children_p.findall(received):
            child = {}
            name = c[1]
            if "/" in name:
                child['path'] = PureFlipperPath(name)
                child['name'] = child['path'].name
            else:
                child['name'] = name
                child['path'] = PureFlipperPath(path / name) # Fancy way to join paths
            if c[0] == "D":
                child['type'] = "dir"
                dirs.append(child)
            elif c[0] == "F":
                child['type'] = "file"
                child['size'] = parse_fs_size(c[2])
                files.append(child)
            children.append(child)
        return {'dirs': dirs, 'files': files, 'children': children}

    def list(self, path: str) -> dict:
        return self._explorer("list", path)

    def tree(self, path: str) -> dict:
        return self._explorer("tree", path)

    def remove(self, file: str) -> None:
        self._serial_wrapper.send(f"storage remove {file}")

    def read(self, file: str) -> bytes:
        """
        Read file from Flipper Zero
        
        Args:
            file (str): File path
            
        Returns:
            bytes: File content
            
        Raises:
            FlipperException: If couldn't read file"""
        try:
            size = self._serial_wrapper.send(f"storage read {file}", read_until='\r\n')
            size = int(size.removeprefix("Size: "))
            if size > 0:
                return self._serial_wrapper.read(size)
            else:
                return b''
        except FlipperError as e:
            if e.messate.startswith("Storage error: invalid name/path"):
                raise # re-raise exception closer to the caller
            else:
                raise e
                  
    def copy(self, src: str, dest: str) -> None:
        self._serial_wrapper.send(f"storage copy {src} {dest}")

    def rename(self, file: str, new_file: str) -> None:
        self._serial_wrapper.send(f"storage rename {file} {new_file}")

    def mkdir(self, new_dir: str) -> None:
        self._serial_wrapper.send(f"storage mkdir {new_dir}")
    
    def md5(self, file: str) -> str:
        received = self._serial_wrapper.send(f"storage md5 {file}").strip()
        if len(received) != 32 or not received.isalnum():
            raise FlipperException(f"Couldn't get MD5 checksum for file {file}")
        return received

    def stat(self, path: str, extended:bool=True) -> dict:
        """
        Get file, directory or storage stats

        Args:
            path (str): File, directory or storage path
            extended (bool, optional)(default: True): If True, returns extended stats (send additional commands to Flipper)

        Returns:
            dict: File, directory or storage stats

        Raises:
            FlipperException: If couldn't parse stats
            StoragePathFree: If path doesn't exist
        """
        path = PureFlipperPath(path)
        try:
            received = self._serial_wrapper.send(f"storage stat {path}").strip()
            if received.startswith("File"):
                received = received.split(", ")
                received[1] = received[1].removeprefix("size: ")
                try:
                    received = {'path': str(path), 'type': 'file', 'size': parse_fs_size(received[1])}
                except ValueError:
                    raise FlipperException(f"Couldn't parse file {path} stats")
                
                if extended:
                    received['md5'] = self.md5(path)
                
            elif received.startswith("Directory"):
                received = {'path': str(path), 'type': 'dir'}
                if extended:
                    tree = self._explorer('tree', path)
                    received['tree'] = tree
                    files = tree['files']
                    total_size = 0
                    for file in files:
                        total_size += file['size']
                    received['total_size'] = total_size
                
            elif received.startswith("Storage"):
                received = received.split(", ")
                received[1] = received[1].removesuffix(" total")
                received[2] = received[2].removesuffix(" free")
                try:
                    received = {'path': str(path), 'type': 'storage', 'total_size': parse_fs_size(received[1]), 'free_space': parse_fs_size(received[2])}
                except ValueError:
                    raise FlipperException(f"Couldn't parse storage {path} stats")

                if extended:
                    tree = self._explorer('tree', path)
                    received['tree'] = tree

                    timestamp = self._serial_wrapper.send(f"storage timestamp {path}")
                    received['last_edit'] = int(timestamp.removeprefix("Timestamp ").strip())

                    infos = self.info(path)
                    received['label'] = infos['label']
                    received['fs_format'] = infos['fs_format']
                    received['total_size'] = infos['total_size'] if infos['total_size'] < received['total_size'] else received['total_size']
                    received['free_space'] = infos['free_space'] if infos['free_space'] < received['free_space'] else received['free_space']
                    received['model'] = infos['model']
                    received['sn'] = infos['sn']
            else:
                raise FlipperException(f"Couldn't parse {path} stats")
        except FlipperError as e:
            if e.args[0].startswith("Storage error: file/dir not exist"):
                raise StoragePathFree(f"Path {path} doesn't exist")   
            else:
                raise FlipperException(e.args[0])
        return received