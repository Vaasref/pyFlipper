import re

from pyflipper.serial import SerialFunction

class Ps(SerialFunction):
    def list(self) -> list:
        pattern = re.compile(
            '(\w+)\s+(0[xX][0-9a-fA-F]+)\s+(\S+)\s+(\d+)\s+(\d+)')
        return [
            {'Name': line[0],
             'Stack start': line[1],
             'Heap': int(line[2]),
             'Stack': int(line[3]),
             'Stack min free': int(line[4])
             } for line in pattern.findall(self._serial_wrapper.send("ps"))
        ]
