import re
import time

from pyflipper.threaded import Threaded
from pyflipper.serial import SerialFunction

# TODO: Leverage pathlib to validate and manage file paths

class Storage(SerialFunction):
    class Write(Threaded):
        def _start(self, file: str) -> None:
            def _run():
                self._serial_wrapper.send(f"storage write {file}")
            self._exec(func=_run)

        def _send(self, text: str) -> None:
            if self._exec_thread.is_alive():
                #replace carriage return with ctrl+Enter
                self._serial_wrapper.write(text.replace('\r\n', '\x0d').encode())
                time.sleep(0.5)
        
        def _check_path(self, path: str) -> None:
            pass

        def file(self, text: str, path: str) -> None:
            self._start(path)
            self._send(text)
            self._stop()

    def __init__(self, flipper) -> None:
        super().__init__(flipper)
        self.write = __class__.Write(flipper)

    def info(self, fs: str) -> dict:
        assert fs in ('/ext', '/int'), "Storage filesystem must be '/ext' or '/int'"
        info_p = re.compile("(\w+):\s(.+)")
        response = self._serial_wrapper.send(f"storage info {fs}")
        info = info_p.findall(response)
        size_p = re.compile("(\d+)KB\s(\w+)")
        size = size_p.findall(response)
        return { info[0][0]: info[0][1].rstrip(), info[1][0]: info[1][1].rstrip(), size[0][1]+"_KB": int(size[0][0]), size[1][1]+"_KB": int(size[1][0])}
    
    def format(self):
        # TODO: implement
        pass

    def _explorer(self, cmd: str, path: str) -> dict:
        dirs_p = re.compile("\[D\]\s(\w+)")
        files_p = re.compile("\[F\]\s(.+)\s(\d+)(\w+)")
        response = self._serial_wrapper.send(f"storage {cmd} {path}")
        dirs = dirs_p.findall(response)
        files = [{'name': file[0], 'size': int(file[1]), 'weight': file[2]} for file in files_p.findall(response)]
        return {'dirs': dirs, 'files': files}

    def list(self, path: str) -> dict:
        return self._explorer("list", path)

    def tree(self, path: str) -> dict:
        return self._explorer("tree", path)

    def remove(self, file: str) -> None:
        self._serial_wrapper.send(f"storage remove {file}")

    def read(self, file: str) -> str:
        try:
            return self._serial_wrapper.send(f"storage read {file}").split('\r\n')[1]
        except IndexError:
            return ""
            
    def copy(self, src: str, dest: str) -> None:
        self._serial_wrapper.send(f"storage copy {src} {dest}")

    def rename(self, file: str, new_file: str) -> None:
        self._serial_wrapper.send(f"storage rename {file} {new_file}")

    def mkdir(self, new_dir: str) -> None:
        self._serial_wrapper.send(f"storage mkdir {new_dir}")
    
    def md5(self, file: str) -> str:
        return self._serial_wrapper.send(f"storage md5 {file}")

    def stat(self, file: str) -> str:
        ret = self._serial_wrapper.send(f"storage stat {file}")

        return self._serial_wrapper.send(f"storage stat {file}")


