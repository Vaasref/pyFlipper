from datetime import datetime

from pyflipper.serial import SerialFunction

class Date(SerialFunction):
    def date(self) -> datetime:
        datetime_str = self._serial_wrapper.send("date")[0:18] # only date and time are needed
        return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

    def timestamp(self) -> float:
        return self.date().timestamp()
    
