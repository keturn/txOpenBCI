# -*- coding: utf-8 -*-
from twisted.internet import reactor
from twisted.application import service
from txopenbci import control

PORT_NAME = '/dev/ttyUSB0'

application = service.Application("OpenBCI")

endpoint = control.serialOpenBCI(PORT_NAME, reactor)

devService = control.DeviceService(endpoint)
devService.setServiceParent(application)
