from datetime import datetime

class Date:
    def __init__(self, serial_wrapper) -> None:
        self._serial_wrapper = serial_wrapper

    def date(self) -> datetime:
        datetime_str = self._serial_wrapper.send("date")[0:18] # only date and time are needed
        return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

    def timestamp(self) -> float:
        return self.date().timestamp()
    
