from pyflipper.threaded import Threaded

class Log(Threaded):
    def attach(self, timeout: int = 10) -> str:
        self._set_watchdog(timeout)
        return self._serial_wrapper.send("log").rstrip("\r\n>:")