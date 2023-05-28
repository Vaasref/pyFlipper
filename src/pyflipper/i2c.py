from pyflipper.serial import SerialFunction

class I2c(SerialFunction):
    def get(self) -> str:
        return self._serial_wrapper.send("i2c")