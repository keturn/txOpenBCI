# -*- coding: utf-8 -*-
"""Sausage. It comes in a tube and you don't want to see how it's made.

This is a mutated version of ometa.protocol.
"""
import functools
from ometa.grammar import OMeta

from twisted.internet.protocol import Protocol, connectionDone
from twisted.python.failure import Failure

from ometa.tube import TrampolinedParser


def makeProtocol(source, sender, receiver, bindings=None, name='Grammar'):
    if bindings is None:
        bindings = {}
    grammar = OMeta(source).parseGrammar(name)
    return functools.partial(
        ParserProtocol, grammar, sender, receiver, bindings)


class ParserProtocol(Protocol):
    """
    A Twisted ``Protocol`` subclass for parsing stream protocols.
    """


    def __init__(self, grammar, sender, receiver, bindings):
        """
        Initialize the parser.

        :param grammar: An OMeta grammar to use for parsing.
        :param sender: A sender with setTransport & stopFlow.
        :param receiver: A receiver with prepareParsing & finishParsing.
        :param bindings: A dict of additional globals for the grammar rules.
        """

        self._grammar = grammar
        self._bindings = dict(bindings)
        self.sender = sender
        self.receiver = receiver
        self._disconnecting = False
        self._parser = TrampolinedParser(
            self._grammar, self.receiver, self._bindings)

    def connectionMade(self):
        """
        Start parsing, since the connection has been established.
        """

        self.sender.setTransport(self.transport)
        self.receiver.prepareParsing(self)

    def dataReceived(self, data):
        """
        Receive and parse some data.

        :param data: A ``str`` from Twisted.
        """

        if self._disconnecting:
            return

        try:
            self._parser.receive(data)
        except Exception:
            # TODO: rethink parser-exception handling. Even if we're treating
            # the error as unrecoverable, we still may want to send a
            # "goodbye" before closing the transport.
            self.connectionLost(Failure())
            try:
                abortConnection = self.transport.abortConnection
            except AttributeError:
                # sadly we might not have abortConnection
                # http://twistedmatrix.com/trac/ticket/5506
                self.transport.loseConnection()
            else:
                abortConnection()
            return

    def connectionLost(self, reason=connectionDone):
        """
        Stop parsing, since the connection has been lost.

        :param reason: A ``Failure`` instance from Twisted.
        """

        if self._disconnecting:
            return
        self.sender.stopFlow()
        self.receiver.finishParsing(reason)
        self._disconnecting = True
