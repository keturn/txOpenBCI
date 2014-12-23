# -*- coding: utf-8 -*-
from twisted.internet import reactor
from twisted.application import service
from twisted.internet.endpoints import serverFromString
from twisted.web.server import Site
from txopenbci import control
from txopenbci.web import Root

PORT_NAME = '/dev/ttyUSB0'

application = service.Application("OpenBCI")

devEndpoint = control.serialOpenBCI(PORT_NAME, reactor)

devService = control.DeviceService(devEndpoint)
devService.setServiceParent(application)

webEndpoint = serverFromString(reactor, "tcp:8088")
webRoot = Root(devService)
webService = Site(webRoot)
webEndpoint.listen(webService)
