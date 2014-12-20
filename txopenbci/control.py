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
import os
import parsley

from twisted.application.service import Service
from twisted.internet.protocol import ClientFactory
from .serial_endpoint import SerialPortEndpoint


BAUD_RATE = 115200

from twisted.python import log

CMD_RESET = b'v'
CMD_STREAM_START = b'b'
CMD_STREAM_STOP = b's'


def serialOpenBCI(serialPortName, reactor):
    return SerialPortEndpoint(serialPortName, reactor, baudrate=BAUD_RATE)


grammar = """
idle = <(~EOT anything)+>:x EOT -> receiver.handleResponse(x)
EOT = '$$$'

sampleStream = sample+
sample = SAMPLE_START <anything{31}>:x SAMPLE_END -> receiver.sampleData(x)
SAMPLE_START = '\xA0'
SAMPLE_END = '\xC0'

debug = anything:x -> receiver.logIncoming(x)
"""


class DeviceCommander(object):
    def __init__(self, transport):
        self._transport = transport

    def _write(self, content):
        return self._transport.write(content)

    def reset(self):
        self._write(CMD_RESET)

    def start_stream(self):
        self._write(CMD_STREAM_START)

    def stop_stream(self):
        log.msg("sending stop command")
        self._write(CMD_STREAM_STOP)

    def hangUp(self):
        self.stop_stream()
        self._transport.loseConnection()


class DeviceReceiver(object):
    currentRule = 'idle'

    def __init__(self, sender):
        """
        :type sender: DeviceCommander
        """
        self.sender = sender
        self._debugLog = None


    def prepareParsing(self, parser):
        self.sender.reset()


    def finishParsing(self, reason):
        pass

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

    def handleSample(self, sample):
        pass

DeviceProtocol = parsley.makeProtocol(grammar, DeviceCommander, DeviceReceiver)


class DeviceProtocolFactory(ClientFactory):
    protocol = DeviceProtocol


class DeviceService(Service):
    _client = None

    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.protoFactory = DeviceProtocolFactory()

    def connect(self):
        if self._client:
            raise RuntimeError("Already connected to %s" % (self._client,))
        self.endpoint.connect(self.protoFactory)\
            .addCallback(self._setClient)

    def _setClient(self, client):
        self._client = client

    def startService(self):
        log.msg("Starting service.")
        Service.startService(self)
        self.connect()

    def stopService(self):
        if self._client:
            self._client.sender.hangUp()
            self._client = None
        Service.stopService(self)
