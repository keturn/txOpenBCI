# -*- coding: utf-8 -*-
"""
To test:
* Service sets ._client after start?
* sensor data!
"""
import gzip
from os import path
from collections import OrderedDict
import parsley
from twisted.python.util import sibpath
from twisted.test.proto_helpers import StringTransport

from twisted.trial.unittest import TestCase
from .control import DeviceProtocol, CMD_RESET, CMD_STREAM_STOP, grammar, \
    python_int32From3Bytes, numpy_int32From3Bytes

try:
    import numpy
except ImportError, e:
    numpy = None
    numpy_reason = e
else:
    numpy_reason = None


def fixture(name):
    filename = sibpath(__file__, path.join('test', name + '.raw'))
    if path.exists(filename + '.gz'):
        # some fixtures are gzipped to prevent git and other tools from messing with
        # their line endings.
        with gzip.open(filename + '.gz') as datafile:
            return datafile.read()
    else:
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
        self.assertEqual(CMD_STREAM_STOP, self.transport.value())
        self.assertTrue(self.transport.disconnecting)


class FakeReceiver(object):
    def __init__(self):
        self.results = []
        self.samples = []

    def handleResponse(self, content):
        self.results.append(content)

    def sampleData(self, *a):
        self.samples.append(a)


class TestGrammar(TestCase):
    def setUp(self):
        self.receiver = FakeReceiver()
        self.grammar = parsley.makeGrammar(grammar, {'receiver': self.receiver})

    def test_resetResponse(self):
        self.grammar(fixture('reset_response')).idle()
        expectedResult = (
            'OpenBCI V3 32bit Board\n'
            'Setting ADS1299 Channel Values\n'
            'ADS1299 Device ID: 0x3E\r\n'
            'LIS3DH Device ID: 0x33\r\n'
        )
        self.assertEqual([expectedResult], self.receiver.results)

    def test_dataSample(self):
        self.grammar(fixture('stream_16samples')).sampleStream()
        samples = self.receiver.samples
        self.assertEqual(16, len(samples))
        self.assertEqual(0, samples[0][0])
        self.assertEqual(15, samples[-1][0])


int24cases = OrderedDict([
    ('max', (b'\x7F\xFF\xFF', 2 ** 23 - 1)),
    ('one', (b'\x00\x00\x01', 1)),
    ('other', (b'\x02\x04\x08', 0x20408)),
    ('another', (b'\x02\x8F\x08', 0x28F08)),
    ('min', (b'\x80\x00\x00', -(2 ** 23))),
    ('neg-one', (b'\xFF\xFF\xFF', -1)),
])


class TestBitTwiddle(TestCase):

    def _test_int32From3Bytes(self, func):
        for name, (in_bytes, number) in int24cases.items():
            result = func(in_bytes)
            self.assertEqual(1, len(result))
            result = result[0]
            self.assertEqual(number, result,
                             "%s: %x is not expected %x" %
                             (name, result, number))

    def test_python_int32From3Bytes(self):
        return self._test_int32From3Bytes(python_int32From3Bytes)

    def test_numpy_int32From3Bytes(self):
        return self._test_int32From3Bytes(numpy_int32From3Bytes)

    if numpy is None:
        test_numpy_int32From3Bytes.skip = "could not load numpy: %s" % (numpy_reason,)
