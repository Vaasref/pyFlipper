from pyflipper.serial import SerialFunction

class Gpio(SerialFunction):
    def mode(self, pin_name: str, value: int) -> None:
        #Set gpio mode: 0 - input, 1 - output
        self._serial_wrapper.send(f"gpio mode {pin_name} {value}")
    
    def set(self, pin_name: str, value: int) -> None:
        self._serial_wrapper.send(f"gpio set {pin_name} {value}")
    
    def read(self, pin_name: str) -> None:
        self._serial_wrapper.send(f"gpio read {pin_name}")