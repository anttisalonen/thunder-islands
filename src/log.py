#!/usr/bin/env python2.7

import logging
import os

logFilename = 'debug.log'

os.unlink(logFilename)
logging.basicConfig(filename = logFilename, level = logging.DEBUG)

def log(msg):
    logging.debug(msg)
