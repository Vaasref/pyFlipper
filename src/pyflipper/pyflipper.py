from logging import debug
from types import MappingProxyType
import serial

from pyflipper.bt import Bt
from pyflipper.debug import Debug
from pyflipper.device_info import DeviceInfo
from pyflipper.free import Free
from pyflipper.i2c import I2c
from pyflipper.ikey import Ikey
from pyflipper.input import Input
from pyflipper.ir import Ir
from pyflipper.led import Led
from pyflipper.log import Log
#from pyflipper.log import Log
from pyflipper.music_player import MusicPlayer
from pyflipper.nfc import NFC
from pyflipper.onewire import Onewire
from pyflipper.ps import Ps
from pyflipper.rfid import RFID
from pyflipper.serial import SerialWrapper, LocalSerial, WSSerial
from pyflipper.storage import Storage
from pyflipper.subghz import Subghz
from pyflipper.vibro import Vibro
from pyflipper.date import Date
from pyflipper.gpio import Gpio
from pyflipper.loader import Loader
from pyflipper.power import Power
from pyflipper.update import Update
from pyflipper.exceptions import SerialException

class PyFlipper:
    _serial_wrapper:SerialWrapper = None
    _info:dict = {}
    info = MappingProxyType(_info)
    name = None

    def __init__(self, **kwargs) -> None:
        """
        Initialize the class.

        This method initializes the class. It takes two arguments, a dictionary
        and a string. The dictionary contains the data that the class will use
        to initialize itself, and the string is the name of the class.

        :param kwargs: A dictionary of data to use to initialize the class.
        :param name: The name of the class.
        :return: None
        """

    def __init__(self, **kwargs) -> None:
        if 'pick_first' not in kwargs:
            kwargs['pick_first'] = "ready"

        if kwargs.get('com'):
            debug("COM port specified, connecting to Flipper Zero")
            self._open_serial(kwargs.get("wrapper", LocalSerial), kwargs['com'])
        elif kwargs.get('ws'):
            debug("Websocket address specified, connecting to Flipper Zero")
            self._open_serial(kwargs.get("wrapper", WSSerial), kwargs['ws'])
        else:
            debug("No COM port or websocket address specified, searching for Flipper Zero devices")
            self._auto_com_search(**kwargs)
        
        if self._serial_wrapper:
            self.vibro = Vibro()
            self.date = Date()
            self.device_info = DeviceInfo()
            self.led = Led()
            self.bt = Bt()
            self.ps = Ps()
            self.free = Free()
            self.storage = Storage()
            self.gpio = Gpio()
            self.loader = Loader()
            self.music_player = MusicPlayer()
            self.power = Power()
            self.update = Update()
            self.log = Log()
            self.nfc = NFC()
            self.rfid = RFID()
            self.subghz = Subghz()
            self.ir = Ir()
            self.ikey = Ikey()
            self.debug = Debug()
            self.onewire = Onewire()
            self.i2c = I2c()
            self.input = Input()
            self._init_name()


    def _init_name(self):
        self.device_info.pull(True)

    @property
    def name(self):
        return self.info.get('name')

    def close(self):
        self._serial_wrapper.close()

    def _open_serial(self, wrapper_class, port,):
        debug(f"Opening serial port {port} using {wrapper_class.__name__}")
        self._serial_wrapper = wrapper_class(port)

    def _auto_com_search(self, **kwargs):
        ports = serial.tools.list_ports.comports()
        match_serial = ""
        if kwargs.get('name'):
            debug(f"Searching for device with name {kwargs.get('name')}")
            match_serial = "FLIP_" + str(kwargs.get('name')).upper()
        flipper_ports = []
        for port in ports:
            try:
                if match_serial:
                    if port.serial_number == match_serial:
                        flipper_ports.append(port.device)
                elif port.serial_number.startswith("FLIP_"):
                    flipper_ports.append(port.device)
            except AttributeError:
                pass
        debug(f"Found {len(flipper_ports)} Flipper Zero devices")
        if len(flipper_ports) == 0:
            raise Exception("No Flipper Zero devices found, please specify COM port or websocket address")
        elif len(flipper_ports) > 1 and not kwargs.get('pick_first'):
            raise Exception("Multiple Flipper Zero devices found, please specify COM port or websocket address")
        else:
            if kwargs.get('pick_first') == 'ready':
                index = 0
                while index < len(flipper_ports):
                    try:
                        debug(f"Trying to connect to {flipper_ports[index]}")
                        self._open_serial(kwargs.get("wrapper", LocalSerial), flipper_ports[index])
                    except SerialException:
                        debug(f"Failed to connect to {flipper_ports[index]}")
                        index += 1
                        if index == len(flipper_ports):
                            raise Exception("No available Flipper Zero devices found, please specify COM port or websocket address")
                    else:
                        debug(f"Connected to {flipper_ports[index]}")
                        break
            else: # either single device or pick_first with no ready check
                debug(f"Connecting to {flipper_ports[0]}")
                self._open_serial(kwargs.get("wrapper", LocalSerial), flipper_ports[0])