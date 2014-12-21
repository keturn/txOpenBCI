# -*- coding: utf-8 -*-
"""
To test:
* Service sets ._client after start?
* sensor data!
"""

from twisted.internet import defer
from twisted.test.proto_helpers import StringTransport

from twisted.trial.unittest import TestCase
from .protocol import CMD_RESET, CMD_STREAM_STOP
from .control import DeviceCommander



class StringTransportEndpoint(object):

    transportClass = StringTransport

    def __init__(self, hostAddress=None, peerAddress=None):
        self.hostAddress = hostAddress
        self.peerAddress = peerAddress
        self.transports = []

    def connect(self, protocolFactory):
        transport = self.transportClass(self.hostAddress, self.peerAddress)
        proto = protocolFactory.buildProtocol(transport.peerAddr)
        proto.makeConnection(transport)
        self.transports.append(transport)
        return defer.succeed(proto)



class TestDeviceCommander(TestCase):
    def setUp(self):
        self.endpoint = StringTransportEndpoint()
        self.commander = DeviceCommander()

    def test_resetOnConnect(self):
        self.commander.connect(self.endpoint)
        transport = self.endpoint.transports[0]
        self.assertEqual(CMD_RESET, transport.value())

    def test_stopOnHangUp(self):
        self.commander.connect(self.endpoint)
        transport = self.endpoint.transports[0]
        transport.clear()
        self.commander.hangUp()
        self.assertEqual(CMD_STREAM_STOP, transport.value())
        self.assertTrue(transport.disconnecting)
