fablib
======

1. Setup::

    $ cd /to/my/project
    $ cat > .gitmodules
    [submodule "fablib"]
	path = fablib
	url = git://github.com/srid/fablib.git
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
    $ fab init

3. No more buildout! ::

    $ bin/python


