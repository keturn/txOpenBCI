# -*- coding: utf-8 -*-
"""
To test:
* sensor data!
"""

from twisted.internet import defer
from twisted.test.proto_helpers import StringTransport

from twisted.trial.unittest import TestCase
from .protocol import CMD_RESET, CMD_STREAM_STOP
from .control import DeviceCommander, DeviceReceiver, RawSample



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

    def test_connectSetsClient(self):
        self.commander.connect(self.endpoint)
        transport = self.endpoint.transports[0]
        self.assertIsNotNone(transport)
        self.assertIsNotNone(self.commander.client)
        self.assertEqual(transport, self.commander.client.transport)

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


class TestDeviceReceiver(TestCase):
    def test_subscribeToSampleData(self):
        # noinspection PyTypeChecker
        receiver = DeviceReceiver(None)
        samples = []
        listener = lambda s: samples.append(s)
        receiver.subscribeToSampleData(listener)
        sample = RawSample(0, (1, 2, 3, 4, 5, 6, 7, 8), (9, 16, 25))
        receiver._publishSample(sample)
        self.assertEqual([sample], samples)

    def test_handleSample(self):
        receiver = DeviceReceiver(None)
        samples = []
        listener = lambda s: samples.append(s)
        receiver.subscribeToSampleData(listener)
        sampleBytes = (
            # eeg data
            b'\x80\x00\x00'  # min
            b'\x7F\xFF\xFF'  # max
            b'\x00\x00\x00'  # zero
            b'\x02\x04\x08'
            b'\x02\x8F\x08'
            b'\xFF\xFF\xFF'  # -1
            b'\x00\x00\x01'  # 1
            b'\x0F\xF0\x0F'
            # accelerometer data
            b'\x7F\x00'
            b'\x00\xFF'
            b'\xFF\xFF'
        )
        receiver.handleSample(0, sampleBytes)
        counter = 0
        eeg = [
            -(2 ** 23),
            2 ** 23 - 1,
            0,
            0x20408,
            0x28F08,
            -1,
            1,
            0xFF00F
        ]
        accelerometer = [
            0x7F00,
            0xFF,
            -1
        ]
        result = samples[0]
        self.assertEqual(counter, result.counter)
        self.assertEqual(eeg, list(result.eeg))
        self.assertEqual(accelerometer, list(result.accelerometer))
