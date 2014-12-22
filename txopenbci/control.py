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
import time
import math

from twisted.application.service import Service
from twisted.internet.endpoints import connectProtocol
from twisted.internet.error import ConnectionClosed
from twisted.python import log

from ._sausage import makeProtocol
from . import protocol

try:
    import numpy
except ImportError, e:
    numpy = None
    numpy_reason = e
else:
    numpy_reason = None

from .serial_endpoint import SerialPortEndpoint


def serialOpenBCI(serialPortName, reactor):
    return SerialPortEndpoint(serialPortName, reactor,
                              baudrate=protocol.BAUD_RATE)



class DeviceSender(object):
    _transport = None

    def setTransport(self, transport):
        self._transport = transport

    def stopFlow(self):
        self._transport = None

    def _write(self, content):
        return self._transport.write(content)

    def reset(self):
        self._write(protocol.CMD_RESET)

    def start_stream(self):
        self._write(protocol.CMD_STREAM_START)

    def stop_stream(self):
        log.msg("sending stop command")
        self._write(protocol.CMD_STREAM_STOP)


class RawSample(object):
    __slots__ = ['counter', 'eeg', 'accelerometer']

    def __init__(self, counter, eeg, accelerometer):
        self.counter = counter
        self.eeg = eeg
        self.accelerometer = accelerometer

    def __hash__(self):
        return hash((self.counter, self.eeg, self.accelerometer))


class DeviceReceiver(object):
    currentRule = 'idle'

    def __init__(self, commander):
        """
        :type commander: DeviceCommander
        """
        self.commander = commander
        self._debugLog = None
        self._sampleSubscribers = set()


    def logIncoming(self, data):
        if not self._debugLog:
            filename = 'debug.%x.raw' % (os.getpid(),)
            self._debugLog = file(filename, 'wb')
        self._debugLog.write(data)


    def handleResponse(self, content):
        log.msg("device response:")
        log.msg(content)
        # sw33t hacks to capture some debug data
        # log.msg("entering debug dump mode")
        # self.currentRule = 'debug'
        # self.sender.start_stream()
        # from twisted.internet import reactor
        # reactor.callLater(0.4, self.sender.stop_stream)


    def handleSample(self, counter, sample):
        # TODO: handle wrapping counter
        # TODO: handle skipped packets
        if self._sampleSubscribers:
            eeg = protocol.int32From3Bytes(sample, 8, 0)
            accelerometer = protocol.accelerometerFromBytes(sample, 24)
            sample = RawSample(counter, eeg, accelerometer)
            self._publishSample(sample)


    def _publishSample(self, sample):
        for listener in self._sampleSubscribers:
            listener(sample)



    # == Interfaces for subscribers ==

    def subscribeToSampleData(self, listener):
        self._sampleSubscribers.add(listener)


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
            protocol.grammar, self.sender, self.receiver,
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
        if not reason.check(ConnectionClosed):
            log.msg("Parser error: %s" % (reason.getErrorMessage(),))
            log.msg(reason.getTraceback())
        else:
            log.msg("Receiver finished: %s" % (reason.getErrorMessage(),))

        self.client = None


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


    def startStream(self):
        self.receiver.currentRule = 'sampleStream'
        self.sender.start_stream()



class TimingWatchdog(object):
    def __init__(self):
        self.times = [float('NaN')] * 250
        self.lastTime = float('NaN')
        self.lastCount = None

    def handleSample(self, sample):
        c = sample.counter
        if self.lastCount is not None:
            increment = (c - self.lastCount) % 256
            if increment != 1:
                dropped = increment - 1
                log.msg("Dropped %s samples (%s..%s)" % (dropped, self.lastCount, c))
        self.lastCount = c
        now = time.clock()
        delta = now - self.lastTime
        self.times[c % 250] = delta
        if (c % 250) == 0 and not math.isnan(delta):
            total = sum(self.times)
            log.msg("Time for 250 samples: %s" % (total,))
        self.lastTime = now


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
