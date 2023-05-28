from pyflipper.serial import SerialFunction

class Debug(SerialFunction):
    def on(self) -> None:
        self._serial_wrapper.send("debug 1")

    def off(self) -> None:
        self._serial_wrapper.send("debug 0")