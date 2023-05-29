import re
from logging import Logger, getLogger

from pyflipper.exceptions import SerialException, FlipperError, FlipperTimeout

class SerialWrapper:
    """
    Abstract class for serial communication

    Raises:
        NotImplementedError: If class is instantiated directly
    """
    serial_log:Logger = getLogger("pyflipper.serial")

    def __init__(self):
        raise NotImplementedError("SerialWrapper is an abstract class, use LocalSerial or WSSerial")

    def _send(self, payload:bytes, until:bytes) -> str:
        raise NotImplementedError("SerialWrapper is an abstract class, use LocalSerial or WSSerial")
    
    def _write(self, payload:bytes):
        raise NotImplementedError("SerialWrapper is an abstract class, use LocalSerial or WSSerial")

    def _read(self, length_bytes:int) -> bytes:
        raise NotImplementedError("SerialWrapper is an abstract class, use LocalSerial or WSSerial")
    
    def _kill_cmd(self):
        raise NotImplementedError("SerialWrapper is an abstract class, use LocalSerial or WSSerial")

    def _close(self):
        raise NotImplementedError("SerialWrapper is an abstract class, use LocalSerial or WSSerial")

    def _error_check(self, received:str):
        pattern = re.compile("\w+\serror:\s.*") # note that it is not infallible
        match = pattern.match(received)
        if match:
            return match.group()
        else:
            return None

    def send(self, payload:str, read_until:str='\r\n>: ') -> str:
        """
        Send command to Flipper Zero and return response

        Args:
            payload (str): Command to send
            read_until (str)(default:'\r\n>:'): String to read until, defaults to prompt

        Raises:
            SerialException: If connection to Flipper Zero is lost
            FlipperError: If Flipper Zero returns an error message

        Returns:
            str: Response from Flipper Zero
        """
        payload = f"{payload}\r".encode() # not sending \n because it would be added in case of writing a file
        read_until = read_until.encode()
        self.serial_log.info(f"Sending: {payload}")
        try:
            received = self._send(payload, read_until)
            error = self._error_check(received)
            if error:
                self.serial_log.error(error)
                raise FlipperError(error)
        except SerialException as e:
            self.serial_log.error(e.args[0])
            raise e
        else:
            display = repr(received)
            if display.count("\\n") > 1: # display as multiline string if there are multiple \n
                display = display.replace("\\n", "\\n\n")
                display = "\n\"\"\"\n{0}\n\"\"\"".format(display[1:-1]) 
            self.serial_log.debug(f"Received: {display}")
        return received
    
    def write(self, msg:bytes):
        """
        Send binary data

        Args:
            msg (bytes): Binary data to send
        
        Raises:
            SerialException: Abstraction for all serial exceptions
        """

        try:
            self.serial_log.debug(f"Sending binary: {msg}")
            self._write(msg)
        except SerialException as e:
            self.serial_log.error(e.args[0])
            raise e
    
    def read(self, length_bytes:int) -> bytes:
        """
        Read binary data

        Args:
            length_bytes (int): Number of bytes to read

        Raises:
            SerialException: Abstraction for all serial exceptions
            ValueError: If length_bytes is not strictly positive

        Returns:
            bytes: Binary data read
        """
        if length_bytes <= 0:
            raise ValueError("length_bytes must be positive")
        self.serial_log.debug(f"Reading {length_bytes} bytes")
        try:
            received = self._read(length_bytes)
        except SerialException as e:
            self.serial_log.error(e.args[0])
            raise e
        else:
            self.serial_log.debug(f"Received: {received}")
        return received
    
    def kill_cmd(self):
        """
        Send kill command (Ctrl+C)  

        Raises:
            SerialException: Abstraction for all serial exceptions
        """
        self.serial_log.debug(f"Sending kill command")
        try:
            self._kill_cmd()
        except SerialException as e:
            self.serial_log.error(e.args[0])
            raise e
    
    def close(self):
        """
        Close serial port
        
        Raises:
            SerialException: Abstraction for all serial exceptions
        """
        self.serial_log.info(f"Closing serial port")
        try:
            self._close()
        except SerialException as e:
            self.serial_log.error(e.args[0])
            raise e



import serial

class LocalSerial(SerialWrapper):
    """
    SerialWrapper class for local serial port

    Args:
        com (str): COM port to connect to

    Raises:
        SerialException: If connection to Flipper Zero fails
    """

    def __init__(self, com):
        try:
            self._serial_port = serial.Serial(port=com, baudrate=9600, bytesize=8, timeout=None, stopbits=serial.STOPBITS_ONE)
            received = self._serial_port.read_until(b'\r\n>: ').decode() #skip welcome banner
        except serial.serialutil.SerialException:
            self.serial_log.error(f"Connection to Flipper Zero on {com} failed, check COM port") # logging manually because SerialWrapper is not initialized
            raise SerialException(f"Connection to Flipper Zero on {com} failed, check COM port")
        else:
            self.serial_log.info(f"Connected to Flipper Zero on {com}")
            self.serial_log.debug("Received: '{}'".format(received))


    @staticmethod
    def _handle_serial_exception(func): # needs to be declared in class to handle exceptions depending on type of serial port
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except serial.SerialTimeoutException as e:
                raise FlipperTimeout("Operation timed out") from e
            except serial.serialutil.SerialException as e:
                raise SerialException("Connection to Flipper Zero lost") from e
        return wrapper


    @_handle_serial_exception
    def _send(self, payload:bytes, until:bytes) -> str:
        self._serial_port.reset_input_buffer()
        self._serial_port.reset_output_buffer()
        self._serial_port.write(payload)
        payload += b'\n' # add \n added in the echo
        self._serial_port.read_until(payload, 1024 * 1024 * 8) # remove echo, 1MiB limit
        received = self._serial_port.read_until(until).decode()
        return received.removesuffix(until.decode())
    

    @_handle_serial_exception
    def _write(self, msg):
        self._serial_port.write(msg)


    @_handle_serial_exception
    def _read(self, length_bytes:int) -> bytes:
        return self._serial_port.read(length_bytes)


    @_handle_serial_exception
    def _kill_cmd(self):
        self._serial_port.reset_output_buffer()
        self._serial_port.write(b'\x03')
    

    @_handle_serial_exception
    def _close(self):
        self._serial_port.close()




import websocket
import socket

class WSSerial(SerialWrapper):
    """
    SerialWrapper class for websocket connection

    Args:
        ws (str): Websocket address to connect to
    
    Raises:
        SerialException: If connection to Flipper Zero fails
    """

    def __init__(self, ws):
        try:
            self._ws = websocket.create_connection(ws)
            received = self._ws.recv() #skip welcome
        except websocket.WebSocketException:
            self.serial_log.error(f"Connection to Flipper Zero on {ws} failed, check websocket address") # logging manually because SerialWrapper is not initialized
            raise SerialException(f"Connection to Flipper Zero on {ws} failed, check websocket address")
        else:
            self.serial_log.info(f"Connected to Flipper Zero on {ws}")
            self.serial_log.debug("Received: '{}'".format(received))
    

    @staticmethod
    def _handle_serial_exception(func): # needs to be declared in class to handle exceptions depending on type of serial port
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except socket.timeout as e:
                raise FlipperTimeout("Operation timed out") from e
            except websocket.WebSocketException as e:
                raise SerialException("Communication error") from e
        return wrapper


    @_handle_serial_exception
    def _clear_buffer(self):
        previous_timeout = self._ws.gettimeout()
        self._ws.settimeout(0.1)
        try:
            while True:
                self._ws.recv()
        except socket.timeout:
            pass
        self._ws.settimeout(previous_timeout)

    
    @_handle_serial_exception
    def _send(self, payload:bytes, read_until:bytes) -> str:
        self._clear_buffer() # Might be needed or not, I don't know, cannot test. If it is not needed, it will just waste 0.1s
        self._ws.send_binary(payload)
        payload += b'\n' # add \n added in the echo
        read_until = read_until.decode()
        line = ""
        while read_until not in line and len(line) < 1024 * 1024 * 8: # 1MiB limit
            line += self._ws.recv()
        line = line.removeprefix(payload.decode()) # remove echo
        return line.removesuffix(read_until)
    

    @_handle_serial_exception
    def _write(self, msg:bytes):
        self._ws.send_binary(msg)


    @_handle_serial_exception
    def _read(self, length_bytes:int) -> bytes:
        return self._ws._recv(length_bytes)


    @_handle_serial_exception
    def _kill_cmd(self):
        self._ws.send_binary(b'\x03')
    

    @_handle_serial_exception
    def _close(self):
        self._ws.close()



import inspect

class SerialFunction:
    """
    This class serves as a base class for all serial functions.
    It is used to get a reference to PyFlipper and its SerialWrapper object without passing it as an argument to every function classes.

    Args:
        flipper (PyFlipper): PyFlipper instance to get SerialWrapper object from

    Raises:
        Exception: If flipper is not passed as argument and cannot be found in caller's frame
    """

    _serial_wrapper:SerialWrapper = None

    def __init__(self, flipper=None):
        if not flipper: # if flipper is not passed, try to get it from caller's frame
            frame = inspect.currentframe()
            while frame:
                caller_frame = frame.f_back
                caller_locals = caller_frame.f_locals
                caller = caller_locals.get('self')
                caller_class = caller.__class__

                if isinstance(caller, SerialFunction): # serves for both super.__init__() calls as well as nested serial functions
                    frame = caller_frame
                elif caller_class.__name__ == "PyFlipper":
                    flipper = caller
                    break
                else:
                    raise Exception("Classes extending SerialFunction must be initialized from PyFlipper object or with a PyFlipper instance passed as argument")

        self._flipper = flipper
        self._serial_wrapper = flipper._serial_wrapper