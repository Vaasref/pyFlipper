
import serial
import re
import websocket
import socket
from logging import Logger, getLogger

from pyflipper.exceptions import SerialException, FlipperErrorException, FlipperTimeoutException

class SerialWrapper:
    """Abstract class for serial communication"""
    serial_log:Logger = getLogger("pyflipper.serial")

    def __init__(self) -> None:
        raise NotImplementedError("SerialWrapper is an abstract class, use LocalSerial or WSSerial")

    def _send(self, payload: str) -> str:
        raise NotImplementedError("SerialWrapper is an abstract class, use LocalSerial or WSSerial")
    
    def _write(self, msg):
        raise NotImplementedError("SerialWrapper is an abstract class, use LocalSerial or WSSerial")
    
    def _kill_cmd(self):
        raise NotImplementedError("SerialWrapper is an abstract class, use LocalSerial or WSSerial")

    def _close(self):
        raise NotImplementedError("SerialWrapper is an abstract class, use LocalSerial or WSSerial")

    def _error_check(self, received: str) -> None:
        pattern = re.compile("\w+\serror:\s.*")
        match = pattern.match(received)
        if match:
            return match.group()
        else:
            return None

    def send(self, payload: str) -> str:
        self.serial_log.info(f"Sending: '{payload}'")
        try:
            received = self._send(payload)
            error = self._error_check(received)
            if error:
                self.serial_log.error(error)
                raise FlipperErrorException(error)
        except SerialException as e:
            self.serial_log.error(e.args[0])
            raise e
        else:
            self.serial_log.debug(f"Received: '{received}'")
        return received
    
    def write(self, msg):
        self.serial_log.debug(f"Sending binary: {msg}")
        self._write(msg)
    
    def kill_cmd(self):
        self.serial_log.debug(f"Sending kill command")
        self._kill_cmd()
    
    def close(self):
        self.serial_log.info(f"Closing serial port")
        self._close()



class LocalSerial(SerialWrapper):
    def __init__(self, com) -> None:
        try:
            self._serial_port = serial.Serial(port=com, baudrate=9600, bytesize=8, timeout=None, stopbits=serial.STOPBITS_ONE)
            received = self._serial_port.read_until(b'>:').decode() #skip welcome banner
        except serial.serialutil.SerialException:
            self.serial_log.error(f"Connection to Flipper Zero on {com} failed, check COM port") # logging manually because SerialWrapper is not initialized
            raise SerialException(f"Connection to Flipper Zero on {com} failed, check COM port")
        else:
            self.serial_log.info(f"Connected to Flipper Zero on {com}")
            self.serial_log.debug("Received: {}".format(received.rstrip('\r\n')))


    @staticmethod
    def _handle_serial_exception(func): # needs to be declared in class to handle exceptions depending on type of serial port
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except serial.SerialTimeoutException as e:
                raise FlipperTimeoutException("Operation timed out") from e
            except serial.serialutil.SerialException as e:
                raise SerialException("Connection to Flipper Zero lost") from e
        return wrapper


    @_handle_serial_exception
    def _send(self, payload: str) -> str:
        self._serial_port.write(f"{payload}\r".encode())
        self._serial_port.readline()
        return self._serial_port.read_until(b'>:').decode().rstrip('\r\n')
    

    @_handle_serial_exception
    def _write(self, msg):
        self._serial_port.write(msg)
    

    @_handle_serial_exception
    def _kill_cmd(self):
        self._serial_port.write(b'\x03')
    

    @_handle_serial_exception
    def _close(self):
        self._serial_port.close()




class WSSerial(SerialWrapper):
    def __init__(self, ws) -> None:
        try:
            self._ws = websocket.create_connection(ws)
            received = self._ws.recv() #skip welcome
        except websocket.WebSocketException:
            self.serial_log.error(f"Connection to Flipper Zero on {ws} failed, check websocket address") # logging manually because SerialWrapper is not initialized
            raise SerialException(f"Connection to Flipper Zero on {ws} failed, check websocket address")
        else:
            self.serial_log.info(f"Connected to Flipper Zero on {ws}")
            self.serial_log.debug("Received: {}".format(received.rstrip('\r\n')))
    

    @staticmethod
    def _handle_serial_exception(func): # needs to be declared in class to handle exceptions depending on type of serial port
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except socket.timeout as e:
                raise FlipperTimeoutException("Operation timed out") from e
            except websocket.WebSocketException as e:
                raise SerialException("Communication error") from e
        return wrapper


    @_handle_serial_exception
    def _send(self, payload: str) -> str:
        self._ws.send_binary(f"{payload}\r".encode())
        line = ""
        while ">:" not in line:
            line += self._ws.recv()
        return line.split(f'{payload}\r\n')[-1].rstrip('\r\n>: ')
    

    @_handle_serial_exception
    def _write(self, msg):
        self._ws.send_binary(msg)


    @_handle_serial_exception
    def _kill_cmd(self):
        self._ws.send_binary(b'\x03')
    

    @_handle_serial_exception
    def _close(self):
        self._ws.close()



import inspect

class SerialFunction:
    _serial_wrapper:SerialWrapper = None

    def __init__(self, flipper=None) -> None:
        if not flipper: # if flipper is not passed, try to get it from caller's frame
            caller_frame = inspect.currentframe().f_back
            caller_locals = caller_frame.f_locals
            flipper = caller_locals.get('self')
            pyflipper_class = caller_locals.get('PyFlipper')
            if not flipper and pyflipper_class and not isinstance(flipper, pyflipper_class):
                raise Exception("SerialFunction must be initialized with flipper object or called from PyFlipper object")

        self._flipper = flipper
        self._serial_wrapper = flipper._serial_wrapper