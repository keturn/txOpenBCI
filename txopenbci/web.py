# -*- coding: utf-8 -*-
import array
import json
from twisted.web.resource import Resource, NoResource
from twisted.web.server import NOT_DONE_YET
from twisted.web.http import ACCEPTED

try:
    import numpy
except ImportError:
    numpy = None
    _arrayTypes = (array.array,)
else:
    _arrayTypes = (numpy.ndarray, array.array)


class ArrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, _arrayTypes):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


_dumps = ArrayEncoder().encode


class Root(Resource):

    def __init__(self, deviceService):
        """
        :type deviceService: txopenbci.control.DeviceService
        """
        Resource.__init__(self)

        self.putChild("control", CommandResource(deviceService))
        self.putChild("stream", SampleStreamer(deviceService))


class CommandResource(Resource):
    isLeaf = True

    def __init__(self, deviceService):
        """
        :type deviceService: txopenbci.control.DeviceService
        """
        Resource.__init__(self)
        self.commander = deviceService.commander

        cmd = self.commander
        self.commandMap = {
            'start': cmd.startStream,
            'stop': cmd.stopStream,
            'reset': cmd.reset,
        }


    def render_POST(self, request):
        commandName = request.postpath
        command = self.commandMap.get(commandName)
        if command is None:
            return NoResource("Command %s not found.").render(request)

        command()
        request.setResponseCode(ACCEPTED)



class SampleStreamer(Resource):

    isLeaf = True

    def __init__(self, deviceService):
        """
        :type deviceService: txopenbci.control.DeviceService
        """
        Resource.__init__(self)
        self.deviceService = deviceService
        self.subscribers = set()
        self.deviceService.commander.receiver.subscribeToSampleData(
            self.handleSample)


    def handleSample(self, sample):
        """
        :type sample: txopenbci.control.RawSample
        """
        if not self.subscribers:
            return

        s = sseMsg([sample.counter, sample.eeg, sample.accelerometer],
                   "sensorData")

        dropouts = []

        for subscriber in self.subscribers:
            if not subscriber.transport.disconnected:
                subscriber.write(s)
            else:
                # can't change subscribers while we're iterating over it
                dropouts.append(subscriber)

        for dropout in dropouts:
            self.subscribers.remove(dropout)


    def render_GET(self, request):
        request.setHeader('Content-type', 'text/event-stream')

        # send an initial message so the client knows we're really here even
        # if there's not currently data streaming.
        request.write(sseMsg('hello', 'keepalive'))

        self.subscribers.add(request)

        return NOT_DONE_YET

    # todo: render_HEAD


def sseMsg(data, name=None):
    """Format a Sever-Sent-Event message.
    :param data: message data, will be JSON-encoded.
    :param name: (optional) name of the event type.
    :rtype: str
    """
    # We need to serialize the message data to a string.  SSE doesn't say that
    # we must use JSON for that, but it's a convenient choice.
    jsonData = _dumps(data)

    # Newlines make SSE messages slightly more complicated.  Fortunately for us,
    # we don't have any in the messages we're using.
    assert '\n' not in jsonData

    if name:
        output = 'event: %s\n' % (name,)
    else:
        output = ''

    output += 'data: %s\n\n' % (jsonData,)
    return output
