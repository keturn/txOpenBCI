# -*- coding: utf-8 -*-
from array import array
from struct import Struct

try:
    import numpy
except ImportError, e:
    numpy = None
    numpy_reason = e
else:
    numpy_reason = None


BAUD_RATE = 115200

CMD_RESET = b'v'
CMD_STREAM_START = b'b'
CMD_STREAM_STOP = b's'

# this is a Parsley (OMeta) grammar describing the protocol we receive
# from the OpenBCI device.
grammar = """
idle = <(~EOT anything)+>:x EOT -> receiver.handleResponse(x)
EOT = '$$$'

sampleStream = sample+
sample = SAMPLE_START
    uint8:counter
    <anything{30}>:x
    SAMPLE_END -> receiver.sampleData(counter, x)
SAMPLE_START = '\xA0'
SAMPLE_END = '\xC0'

debug = anything:x -> receiver.logIncoming(x)
uint8 = anything:x -> ord(x)
"""
# The ADS1299 outputs 24 bits of data per channel in binary twos complement
# format, MSB first [data sheet SBAS499A]. OpenBCI passes it through in that
# format to us, but most platforms do not have a 24-bit integer type, and
# we're probably not using that big-endian byte order.

# 24-bit integer is unusual enough that struct and numpy don't have tools
# to unpack them, but we can treat it as a signed 8-bit part followed by
# unsigned 16 bits and then reassemble.

_i3Struct = [Struct('>' + ('bH' * (n + 1))) for n in range(8)]


def python_int32From3Bytes(buf, count=-1, offset=0):
    """
    Turn a byte buffer containing 24-bit big-endian data into
    an array of python integers.
    """
    if count == -1:
        count = len(buf) / 3
    sizedStruct = _i3Struct[count - 1]
    # this unpacks to an alternating sequence of high bytes and lower 16-bits
    parts = sizedStruct.unpack_from(buf, offset=offset)
    high = parts[::2]  # start by grabbing the high bytes
    output = array('l', high)  # put them into an array of 32-bit ints
    for i, low in enumerate(parts[1::2]):
        output[i] <<= 16  # push them up by 16 bits
        output[i] |= low  # fill in the lower 16 bits
    return output


if numpy:
    _i1u2 = numpy.dtype([('high', 'i1'), ('low', '>u2')])


def numpy_int32From3Bytes(buf, count=-1, offset=0):
    """
    Turn a byte buffer containing 24-bit big-endian data into
    a numpy array of 32-bit integers.
    """
    in_array = numpy.frombuffer(buf, _i1u2, count=count, offset=offset)
    output = in_array['high'].astype('i4')
    output <<= 16
    output |= in_array['low']
    return output


if numpy:
    int32From3Bytes = numpy_int32From3Bytes
else:
    int32From3Bytes = python_int32From3Bytes

