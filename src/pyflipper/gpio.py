from pyflipper.serial import SerialFunction
from pyflipper.exceptions import FlipperException

class Gpio(SerialFunction):
    def __init__(self, flipper=None) -> None:
        super().__init__(flipper)
        self.available_pins = self.load_available_pins()

    def load_available_pins(self) -> tuple:
        """
        Reload available GPIO pins

        Returns:
            tuple: Available GPIO pins

        Raises:
            FlipperException: If couldn't load available GPIO pins
        """
        received = self._serial_wrapper.send("gpio mode -")
        received = received.split("Available pins: ")
        if len(received) != 2:
            raise FlipperException("Couldn't load available GPIO pins")
        received = received[1].strip()
        self.available_pins = tuple(received.split(" "))
        if len(self.available_pins) == 0:
            raise FlipperException("Couldn't load available GPIO pins")
        return self.available_pins

    def mode(self, pin_name: str, mode: int) -> None:
        """
        Set GPIO pins mode
        
        Args:
            pin_name (str): GPIO pin name
            mode (int): GPIO pin mode (0 - input, 1 - output)
        
        Raises:
            ValueError: If pin_name doesn't correspond to an available pin
            ValueError: If mode is not 0 or 1
        """
        if mode not in (0, 1):
            raise ValueError("GPIO mode must be 0 or 1")
        if pin_name not in self.available_pins:
            raise ValueError("GPIO pin not available")
        self._serial_wrapper.send(f"gpio mode {pin_name} {mode}")
    
    def set(self, pin_name: str, value: int) -> None:
        """
        Set GPIO pins value
        
        Args:
            pin_name (str): GPIO pin name
            value (int): GPIO pin value (0 - low, 1 - high)
        
        Raises:
            ValueError: If pin_name doesn't correspond to an available pin
            ValueError: If value is not 0 or 1
        """
        if value not in (0, 1):
            raise ValueError("GPIO value must be 0 or 1")
        if pin_name not in self.available_pins:
            raise ValueError("GPIO pin not available")
        self._serial_wrapper.send(f"gpio set {pin_name} {value}")
    
    def read(self, pin_name: str) -> None:
        """
        Read GPIO pins value

        Args:
            pin_name (str): GPIO pin name

        Raises:
            ValueError: If pin_name doesn't correspond to an available pin
        """
        if pin_name not in self.available_pins:
            raise ValueError("GPIO pin not available")
        self._serial_wrapper.send(f"gpio read {pin_name}")