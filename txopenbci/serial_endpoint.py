# -*- coding: utf-8 -*-
# Yoinked from https://twistedmatrix.com/trac/ticket/4847
# should be retired in favor of the mainline twisted code when that gets merged
# and released.
from twisted.internet.error import getConnectError
from twisted.internet import defer
from twisted.python.util import FancyEqMixin
from zope.interface import implementer
from twisted.internet.interfaces import IAddress, IStreamClientEndpoint


@implementer(IAddress)
class SerialAddress(FancyEqMixin, object):
    """
    An L{interfaces.IAddress} provider for serial port connections.
    @ivar name: The device name associated with this port
    @type name: C{str}
    """

    compareAttributes = ('name', )

    def __init__(self, name):
        self.name = name


    def __repr__(self):
        return 'SerialAddress(%r)' % (self.name,)


    def __hash__(self):
        return hash(self.name)


@implementer(IStreamClientEndpoint)
class SerialPortEndpoint(object):
    """
    A Serial Port endpoint.
    @type _serialport: L{serialport} module
    @ivar _serialport: A hook used for testing availability of serial port
        support.
    """
    try:
        from twisted.internet.serialport import SerialPort as _serialport
    except ImportError:
        _serialport = None


    def __init__(self, deviceNameOrPortNumber, reactor, *args, **kwargs):
        """
        @see: L{serialport.SerialPort}
        """
        self._deviceNameOrPortNumber = deviceNameOrPortNumber
        self._reactor = reactor
        self._args = args
        self._kwargs = kwargs


    def connect(self, serialFactory):
        """
        Implement L{IStreamClientEndpoint.connect} to connect to serial ports
        @param serialFactory: The protocol factory which will build protocols
            for connections to this service.
        @type serialFactory: L{twisted.internet.interfaces.IProtocolFactory}
        """
        try:
            if self._serialport is None:
                raise ImportError
            else:
                # noinspection PyArgumentList
                proto = serialFactory.buildProtocol(
                    SerialAddress(self._deviceNameOrPortNumber)  )
                self._serialport(proto, self._deviceNameOrPortNumber,
                        self._reactor, *self._args, **self._kwargs)
                return defer.succeed(proto)
        except Exception, e:
            return defer.fail(getConnectError(e))