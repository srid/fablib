fablib
======

fablib is a helper library for `Fabric <http://fabfile.org>`_ to setup a
sandboxed Python environment (virtualenv) for your project without the overhead
of having to use Buildout.

Installation
------------

1. Setup::

    $ cd /to/my/project
    $ git submodule add git://github.com/srid/fablib.git fablib
    $ cat > fabfile.py
    import sys
    from os import path
    from fabric.api import *
    # Import github.com/srid/fablib
    sys.path.append(path.abspath(
        path.join(path.dirname(__file__), 'fablib')))
    import venv
    
    clean = venv.clean
    init = venv.init
    
2. Use::

    $ fab -l
    $ fab clean
    $ fab init    # `fab init:pyver=3.1` for Py3k!

3. No more buildout! ::

    $ bin/python

See the `applib`__ project for a real-world example.

Features
--------

* Create virtualenv and install packages (including dependencies)
* Automatically include PyWin32 from global site-packages
* Use `PyPM <http://code.activestate.com/pypm>`_ (instead of pip) if available
  -- saves a lot of time. Requires ActivePython.

.. __: http://github.com/ActiveState/applib/blob/master/fabfile.py#L1

