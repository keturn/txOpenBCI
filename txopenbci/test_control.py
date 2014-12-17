# -*- coding: utf-8 -*-
"""
To test:
* Service sets ._client after start?
* We can get the response from the "reset" command as an event with its contents
* sensor data!
"""
from twisted.test.proto_helpers import StringTransport

from twisted.trial.unittest import TestCase
from .control import DeviceProtocol, CMD_RESET, CMD_STOP


class TestDeviceProtocol(TestCase):
    def setUp(self):
        self.protocol = DeviceProtocol()
        self.transport = StringTransport()

    def test_resetOnConnect(self):
        self.protocol.makeConnection(self.transport)
        self.assertEqual(CMD_RESET, self.transport.value())

    def test_stopOnHangUp(self):
        self.protocol.makeConnection(self.transport)
        self.transport.clear()
        self.protocol.hangUp()
        self.assertEqual(CMD_STOP, self.transport.value())
        self.assertTrue(self.transport.disconnecting)
