from .bt import Bt
from .debug import Debug
from .device_info import DeviceInfo
from .free import Free
from .i2c import I2c
from .ikey import Ikey
from .input import Input
from .ir import Ir
from .led import Led
from .log import Log
#from .log import Log
from .music_player import MusicPlayer
from .nfc import NFC
from .onewire import Onewire
from .ps import Ps
from .rfid import RFID
from .serial_wrapper import LocalSerial, WSSerial
from .storage import Storage
from .subghz import Subghz
from .vibro import Vibro
from .date import Date
from .gpio import Gpio
from .loader import Loader
from .power import Power
from .update import Update

class PyFlipper:

    def __init__(self, **kwargs) -> None:
        assert bool(kwargs.get('com')) ^ bool(kwargs.get('ws')), "COM or Websocket required"
        if kwargs.get('com'):
                self._serial_wrapper = LocalSerial(com=kwargs['com'])
        else:
                self._serial_wrapper = WSSerial(ws=kwargs['ws']) 
        self.vibro = Vibro(serial_wrapper=self._serial_wrapper)
        self.date = Date(serial_wrapper=self._serial_wrapper)
        self.device_info = DeviceInfo(serial_wrapper=self._serial_wrapper)
        self.led = Led(serial_wrapper=self._serial_wrapper)
        self.bt = Bt(serial_wrapper=self._serial_wrapper)
        self.ps = Ps(serial_wrapper=self._serial_wrapper)
        self.free = Free(serial_wrapper=self._serial_wrapper)
        self.storage = Storage(serial_wrapper=self._serial_wrapper)
        self.gpio = Gpio(serial_wrapper=self._serial_wrapper)
        self.loader = Loader(serial_wrapper=self._serial_wrapper)
        self.music_player = MusicPlayer(serial_wrapper=self._serial_wrapper)
        self.power = Power(serial_wrapper=self._serial_wrapper)
        self.update = Update(serial_wrapper=self._serial_wrapper)
        self.log = Log(serial_wrapper=self._serial_wrapper)
        self.nfc = NFC(serial_wrapper=self._serial_wrapper)
        self.rfid = RFID(serial_wrapper=self._serial_wrapper)
        self.subghz = Subghz(serial_wrapper=self._serial_wrapper)
        self.ir = Ir(serial_wrapper=self._serial_wrapper)
        self.ikey = Ikey(serial_wrapper=self._serial_wrapper)
        self.debug = Debug(serial_wrapper=self._serial_wrapper)
        self.onewire = Onewire(serial_wrapper=self._serial_wrapper)
        self.i2c = I2c(serial_wrapper=self._serial_wrapper)
        self.input = Input(serial_wrapper=self._serial_wrapper)