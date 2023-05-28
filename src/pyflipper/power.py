import re

from pyflipper.serial import SerialFunction

class Power(SerialFunction):
    def off(self) -> None:
        return self._serial_wrapper.send("power off")

    def reboot(self) -> None:
        return self._serial_wrapper.send("power reboot")
    
    def reboot2dfu(self) -> None:
        return self._serial_wrapper.send("power reboot2dfu")
    
    def info(self) -> dict:
        pattern = re.compile("([\w|_]+)\s+:\s([\w|\d]+)")
        items = pattern.findall(self._serial_wrapper.send("power info"))
        return {x: int(y) if y.isdigit() else y for x, y in items}
    
