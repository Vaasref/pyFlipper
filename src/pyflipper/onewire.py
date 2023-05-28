from pyflipper.serial import SerialFunction

class Onewire(SerialFunction):
    def search(self) -> str:
        return self._serial_wrapper.send("onewire search")