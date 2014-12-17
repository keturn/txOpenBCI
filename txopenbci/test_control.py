# -*- coding: utf-8 -*-
"""
To test:
* Service sets ._client after start?
* sensor data!
"""
from os import path
import parsley
from twisted.python.util import sibpath
from twisted.test.proto_helpers import StringTransport

from twisted.trial.unittest import TestCase
from .control import DeviceProtocol, CMD_RESET, CMD_STOP, grammar


def fixture(name):
    filename = sibpath(__file__, path.join('test', name + '.raw'))
    with file(filename, 'rb') as datafile:
        return datafile.read()


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
        self.protocol.sender.hangUp()
        self.assertEqual(CMD_STOP, self.transport.value())
        self.assertTrue(self.transport.disconnecting)


class TestGrammar(TestCase):
    def test_resetResponse(self):

        class FakeReceiver(object):
            def __init__(self):
                self.results = []

            def handleResponse(self, content):
                self.results.append(content)

        receiver = FakeReceiver()

        parse = parsley.makeGrammar(grammar, {'receiver': receiver})
        parse(fixture('reset_response')).idle()
        expectedResult = (
            'OpenBCI V3 32bit Board\n'
            'Setting ADS1299 Channel Values\n'
            'ADS1299 Device ID: 0x3E\r\n'
            'LIS3DH Device ID: 0x33\r\n'
        )
        self.assertEqual([expectedResult], receiver.results)
