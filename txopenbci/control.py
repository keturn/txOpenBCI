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


from twisted.application.service import Service
from twisted.internet.protocol import ClientFactory, Protocol
from txopenbci.serial_endpoint import SerialPortEndpoint


BAUD_RATE = 115200

from twisted.python import log

CMD_RESET = b'v'
CMD_STOP = b's'


def serialOpenBCI(serialPortName, reactor):
    return SerialPortEndpoint(serialPortName, reactor, baudrate=BAUD_RATE)


class DeviceCommander(object):
    def __init__(self, protocol):
        self._protocol = protocol

    def _write(self, content):
        return self._protocol.transport.write(content)

    def reset(self):
        self._write(CMD_RESET)

    def stop_stream(self):
        self._write(CMD_STOP)


class DeviceProtocol(Protocol):

    def __init__(self):
        self.command = DeviceCommander(self)

    def connectionMade(self):
        log.msg("*** Connected!")
        self.command.reset()

    def connectionLost(self, reason=None):
        log.msg("*** Disconnected! %s" % (reason,))
        del self.command

    def dataReceived(self, data):
        log.msg("%s: %s" % (len(data), data))

    def hangup(self):
        self.command.stop_stream()
        self.transport.loseConnection()


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
            self._client.hangup()
            self._client = None
        Service.stopService(self)
