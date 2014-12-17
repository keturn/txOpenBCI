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
import parsley

from twisted.application.service import Service
from twisted.internet.protocol import ClientFactory
from .serial_endpoint import SerialPortEndpoint


BAUD_RATE = 115200

from twisted.python import log

CMD_RESET = b'v'
CMD_STOP = b's'


def serialOpenBCI(serialPortName, reactor):
    return SerialPortEndpoint(serialPortName, reactor, baudrate=BAUD_RATE)


grammar = """
idle = <(~EOT anything)+>:x EOT -> receiver.handleResponse(x)
EOT = '$$$'
"""


class DeviceCommander(object):
    def __init__(self, transport):
        self._transport = transport

    def _write(self, content):
        return self._transport.write(content)

    def reset(self):
        self._write(CMD_RESET)

    def stop_stream(self):
        self._write(CMD_STOP)

    def hangUp(self):
        self.stop_stream()
        self._transport.loseConnection()


class DeviceReceiver(object):
    currentRule = 'idle'

    def __init__(self, sender):
        self.sender = sender


    def prepareParsing(self, parser):
        self.sender.reset()


    def finishParsing(self, reason):
        pass


    def handleResponse(self, content):
        log.msg(content)


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
