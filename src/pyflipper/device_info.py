import re

from pyflipper.serial import SerialFunction

class DeviceInfo(SerialFunction):
    def pull(self, update_flipper_instance:bool=True) -> dict:
        pattern = re.compile("([\w|_]+)\s+:\s([\w|\d]+)")
        value = {}

        for x in pattern.findall(self._serial_wrapper.send("device_info")):
            if x[1].isdigit():
                value[x[0]] = int(x[1])

            elif x[1] in ["true", "false"]:
                value[x[0]] = x[1] == "true"

            else:
                value[x[0]] = x[1]
        if update_flipper_instance:
            self._flipper._info = value.copy()
        return value