# -*- coding: utf-8 -*-
"""
To test:
* Service sets ._client after start?
* We send "stop streaming" on disconnect?
* We can get the response from the "reset" command as an event with its contents
* sensor data!
"""
from twisted.test.proto_helpers import StringTransport

from twisted.trial.unittest import TestCase
from .control import DeviceProtocol, CMD_RESET


class TestDeviceProtocol(TestCase):
    def test_resetOnConnect(self):
        protocol = DeviceProtocol()
        transport = StringTransport()
        protocol.makeConnection(transport)
        self.assertEqual(CMD_RESET, transport.value())
