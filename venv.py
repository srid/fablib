"""Virtualenv utilities for fabric"""

def clean():
    """Delete all files/directories ignored in source control
    
    The following source control systems are supported:
    
      svn --    svn:ignore
      
    The idea is to eventually to delete virtualenv-created files to start
    from scratch.
    """
    # TODO: support git and hg
    root = path.dirname(__file__)
    ignores = local('svn propget svn:ignore {root}'.format(
        root=root)).splitlines()
    for ignore in ignores:
        ignore = ignore.strip()
        if not ignore: continue
        
        for pth in glob(path.join(root, ignore)):
            print('Deleting {0}'.format(pth))
            if path.isdir(pth):
                shutil.rmtree(pth)
            else:
                os.remove(pth)


def init(pyver='2.7', upgrade=False, apy=False):
    """Create a virtualenv and setup entry points
    
    Poor man's buildout (supports py3k too!). You will need to have virtualenv
    and virtualenv5 installed before running this command.
    
      pyver             -- The Python version to use (eg: 2.7)
      upgrade           -- Should we upgrade installed packages?
      apy               -- Must use ActivePython
      
    TODO: support installing [extra] requirements as 'setup.py develop' will
          not install them.
    """
    py = _get_python(pyver)
    virtualenv = 'virtualenv5' if pyver[0] == '3' else 'virtualenv'

    # must be ActivePython
    if apy:
        local('{0} -m activestate'.format(py))

    # create virtualenv
    venv_cmd = '{0} --no-site-packages -p {1} {2}'.format(virtualenv, py, '.')
    local(venv_cmd, capture=False)

    # find paths to essential binaries in the created virtualenv
    scripts_dir = 'Scripts' if WIN else 'bin'
    python_exe = path.join(scripts_dir, 'python.exe' if WIN else 'python')
    ez_exe = path.join(scripts_dir, 'easy_install.exe' if WIN else \
                       'easy_install')
    pip_exe = path.join(scripts_dir, 'pip.exe' if WIN else 'pip')

    def install(pkg, force_upgrade=False):
        if path.exists(pip_exe):
            install_cmd = '{0} install {1} {{0}}'.format(
                pip_exe, '-U' if upgrade or force_upgrade else '')
        else:
            # pip exe doesn't exist (python3?); fallback to easy_install
            install_cmd = '{0} {1} {{0}}'.format(
                ez_exe, '-U' if upgrade or force_upgrade else '')
        local(install_cmd.format(pkg))
        
    if WIN:
        # Stupid virtualenv exits immediately to console on Windows, leaving
        # it running as a background process.
        print('Waiting for virtualenv to finish (10 secs) ...')
        time.sleep(10)
        
    # upgrade to latest distribute; virtualenv must have installed an outdated
    # version.
    install('distribute', force_upgrade=True)

    # setup dev environment
    local('{0} setup.py develop'.format(python_exe))


def _get_python(pyver):
    if sys.platform == 'win32':
        # TODO: support non-ActivePython as well
        # TODO: change to pythonX.Y once newer versions of APy is released
        python = 'python{pyver[0]}{pyver[2]}.exe'.format(pyver=pyver)
    elif sys.platform == 'darwin':
        python = '/Library/Frameworks/Python.framework/Versions/{pyver}/bin/python{pyver}'.format(
            pyver=pyver)
    else:
        python = 'python' + pyver

    return python
