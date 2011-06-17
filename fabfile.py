# Copyright (c) 2010 ActiveState Software Inc. All rights reserved.

from fabric.api import *

import venv


clean = venv.clean
init = venv.init


def init32():
    return init(pyver='3.2')
