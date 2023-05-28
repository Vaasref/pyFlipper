from threading import Thread, Event
import time

from pyflipper.serial import SerialFunction
from pyflipper.serial import SerialWrapper


class Threaded(SerialFunction):
    _exec_thread:Thread = None
    _watchdog:Thread = None

    def _exec(self, func, timeout:float=0.0, *args, **kwargs) -> None:  
        if self._exec_thread:
            if self._exec_thread.is_alive():
                raise Exception(f"Thread {self._exec_thread.name} is already running")
            else:
                raise Exception(f"Thread {self._exec_thread.name} was not properly stopped and purged")

        self._exec_thread = Task(func, *args, **kwargs)
        self._exec_thread.start()
        if timeout:
            self._set_watchdog(timeout)
        else:
            self._watchdog = None

    def _set_watchdog(self, timeout:float = 5) -> None:
        self._watchdog = Watchdog(self, timeout)
        self._watchdog.start()
    
    def _hush_watchdog(self) -> None:
        if self._watchdog:
            self._watchdog = None
        else:
            raise 

    def _stop(self) -> None:
        if self._watchdog or self._exec_thread and self._exec_thread.is_alive():
            if self._exec_thread:
                self._exec_thread._stop()
            self._serial_wrapper.kill_cmd()
        self._watchdog = None
        self._exec_thread = None

class Task(Thread):
    def __init__(self, func, *args, **kwargs) -> None:
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._stop_event = Event()

    def run(self):
        self.func(*self.args, **self.kwargs)
        if self._exec_thread == self:
            self._exec_thread = None
    
    def _stop(self):
        self._stop_event.set()

class Watchdog(Thread):
    def __init__(self, owner:Threaded, timeout:float) -> None:
        self.owner = owner
        self.timeout = timeout

    def run(self):
        time.sleep(self.timeout)
        if self.owner._watchdog == self:
            self.owner._stop()