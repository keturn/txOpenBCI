# -*- coding: utf-8 -*-
""" 
"""  # TODO: module docstring
import csv
import math
import os
import time
from twisted.python import log


class SensorLog(object):
    """Log the sensor data to disk."""

    logfile = None
    writer = None
    time0 = None

    def __init__(self):
        self._rowBuffer = [''] * (1 + 8 + 3 + 1)


    def _openLog(self):
        self.time0 = time.time()
        filename = 'sensor.%x.%x.csv' % (os.getpid(), self.time0)
        self.logfile = file(filename, 'wb')
        self.writer = csv.writer(self.logfile)
        self.writer.writerow([
            'count',
            's1', 's2', 's3', 's4', 's5', 's6', 's7', 's8',
            'x', 'y', 'z',
            'clock'
        ])


    def handleSample(self, sample):
        """
        :type sample: RawSample
        """
        if not self.writer:
            self._openLog()

        self._rowBuffer[0] = sample.counter
        self._rowBuffer[1:9] = sample.eeg
        self._rowBuffer[9:12] = sample.accelerometer
        self._rowBuffer[12] = time.time() - self.time0

        self.writer.writerow(self._rowBuffer)


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
        now = time.time()
        delta = now - self.lastTime
        self.times[c % 250] = delta
        if (c % 250) == 0 and not math.isnan(delta):
            total = sum(self.times)
            log.msg("Time for 250 samples: %s" % (total,))
        self.lastTime = now