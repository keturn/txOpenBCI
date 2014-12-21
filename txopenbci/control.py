# -*- coding: utf-8 -*-
"""
Players:

* one who makes sure a connection to the device is open
  - a stable presence in the community; everyone knows where to find them
* one who holds the connection to the device
  - may come and go with the connection
* one who knows how to command the device
* one who hears what the device tells us
* those who listen, and interpret
* those who listen, and record
* those who listen, and display
"""
from array import array
import os
from struct import Struct

from twisted.application.service import Service
from twisted.internet.endpoints import connectProtocol
from twisted.python import log

from ._sausage import makeProtocol

try:
    import numpy
except ImportError, e:
    numpy = None
    numpy_reason = e
else:
    numpy_reason = None

from .serial_endpoint import SerialPortEndpoint

BAUD_RATE = 115200

CMD_RESET = b'v'
CMD_STREAM_START = b'b'
CMD_STREAM_STOP = b's'


def serialOpenBCI(serialPortName, reactor):
    return SerialPortEndpoint(serialPortName, reactor, baudrate=BAUD_RATE)

# this is a Parsley (OMeta) grammar describing the protocol we receive
# from the OpenBCI device.
grammar = """
idle = <(~EOT anything)+>:x EOT -> receiver.handleResponse(x)
EOT = '$$$'

sampleStream = sample+
sample = SAMPLE_START
    uint8:counter
    <anything{30}>:x
    SAMPLE_END -> receiver.sampleData(counter, x)
SAMPLE_START = '\xA0'
SAMPLE_END = '\xC0'

debug = anything:x -> receiver.logIncoming(x)
uint8 = anything:x -> ord(x)
"""


# The ADS1299 outputs 24 bits of data per channel in binary twos complement
# format, MSB first [data sheet SBAS499A]. OpenBCI passes it through in that
# format to us, but most platforms do not have a 24-bit integer type, and
# we're probably not using that big-endian byte order.

# 24-bit integer is unusual enough that struct and numpy don't have tools
# to unpack them, but we can treat it as a signed 8-bit part followed by
# unsigned 16 bits and then reassemble.

_i3Struct = [Struct('>' + ('bH' * (n + 1))) for n in range(8)]


def python_int32From3Bytes(buf, count=-1, offset=0):
    """
    Turn a byte buffer containing 24-bit big-endian data into
    an array of python integers.
    """
    if count == -1:
        count = len(buf) / 3
    sizedStruct = _i3Struct[count - 1]
    # this unpacks to an alternating sequence of high bytes and lower 16-bits
    parts = sizedStruct.unpack_from(buf, offset=offset)
    high = parts[::2]  # start by grabbing the high bytes
    output = array('l', high)  # put them into an array of 32-bit ints
    for i, low in enumerate(parts[1::2]):
        output[i] <<= 16  # push them up by 16 bits
        output[i] |= low  # fill in the lower 16 bits
    return output


if numpy:
    _i1u2 = numpy.dtype([('high', 'i1'), ('low', '>u2')])


def numpy_int32From3Bytes(buf, count=-1, offset=0):
    """
    Turn a byte buffer containing 24-bit big-endian data into
    a numpy array of 32-bit integers.
    """
    in_array = numpy.frombuffer(buf, _i1u2, count=count, offset=offset)
    output = in_array['high'].astype('i4')
    output <<= 16
    output |= in_array['low']
    return output


if numpy:
    int32From3Bytes = numpy_int32From3Bytes
else:
    int32From3Bytes = python_int32From3Bytes


class DeviceSender(object):
    _transport = None

    def setTransport(self, transport):
        self._transport = transport

    def stopFlow(self):
        self._transport = None

    def _write(self, content):
        return self._transport.write(content)

    def reset(self):
        self._write(CMD_RESET)

    def start_stream(self):
        self._write(CMD_STREAM_START)

    def stop_stream(self):
        log.msg("sending stop command")
        self._write(CMD_STREAM_STOP)


class DeviceReceiver(object):
    currentRule = 'idle'

    def __init__(self, commander):
        """
        :type commander: DeviceCommander
        """
        self.commander = commander
        self._debugLog = None


    def logIncoming(self, data):
        if not self._debugLog:
            filename = 'debug.%x.raw' % (os.getpid(),)
            self._debugLog = file(filename, 'wb')
        self._debugLog.write(data)


    def handleResponse(self, content):
        log.msg(content)
        # sw33t hacks to capture some debug data
        # log.msg("entering debug dump mode")
        # self.currentRule = 'debug'
        # self.sender.start_stream()
        # from twisted.internet import reactor
        # reactor.callLater(0.4, self.sender.stop_stream)


    def handleSample(self, counter, sample):
        pass


    # prepareParsing and finishParsing are not called from the grammar, but
    # from the ParserProtocol, as connection-related events.

    def prepareParsing(self, parser):
        self.commander.deviceOpen()


    def finishParsing(self, reason):
        self.commander.deviceLost(reason)




class DeviceCommander(object):

    _senderFactory = DeviceSender
    _connecting = None

    def __init__(self):
        self.client = None
        self.sender = DeviceSender()
        self.receiver = DeviceReceiver(self)
        self._protocolClass = makeProtocol(
            grammar, self.sender, self.receiver,
            name="OpenBCIDevice")

    def connect(self, endpoint):
        if self.client:
            raise RuntimeError("Already connected to %s" % (self.client,))
        if self._connecting:
            raise RuntimeError("Connection already in progress.")
        self._connecting = connectProtocol(endpoint, self._protocolClass())
        self._connecting.addCallbacks(self._setClient, self._connectFailed)

    def _setClient(self, client):
        self.client = client
        self._connecting = None

    def _connectFailed(self, reason):
        log.msg(reason.getErrorMessage())
        self._connecting = None


    # == Events we get from DeviceReceiver ==

    def deviceOpen(self):
        # Send the reset command, so we know we're starting with a predictable
        # state.
        self.sender.reset()


    def deviceLost(self, reason):
        log.msg("Receiver finished: %s" % (reason.getErrorMessage(),))
        self.client = None
        self.sender.stopFlow()  # should be lower-level


    # == Outward-facing commands: ==

    def hangUp(self):
        if self.client:
            self.sender.stop_stream()
            self.client.transport.loseConnection()

    def destroy(self):
        self.hangUp()
        self.client = None
        if self._connecting:
            self._connecting.cancel()



class DeviceService(Service):

    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.commander = DeviceCommander()

    def startService(self):
        log.msg("Starting service.")
        if numpy_reason:
            log.msg("Note: numpy is not available: %s" % (numpy_reason,))
        Service.startService(self)
        self.commander.connect(self.endpoint)

    def stopService(self):
        self.commander.destroy()
        Service.stopService(self)
