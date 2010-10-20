"""Virtualenv utilities for fabric"""

import os
from os import path
import sys
import shutil
import time

from fabric.api import *

WIN = sys.platform == 'win32'


def clean():
    """Delete all files/directories ignored in source control
    
    The following source control systems are supported:
    
      svn --    svn:ignore
      
    The idea is to eventually to delete virtualenv-created files to start
    from scratch.
    """
    from glob import glob
    
    root = path.abspath('.')
    
    # Read ignore patterns
    if path.exists(path.join(root, '.svn')):
        ignores = local('svn propget svn:ignore {0}'.format(root)).splitlines()
    elif path.exists(path.join(root, '.git')):
        gitignore = path.join(root, '.gitignore')
        if path.exists(gitignore):
            ignores = open(gitignore).readlines()
        else:
            ignores = []
    else:
        raise IOError('unsupported source control at %s' % root)
        
    # Strip ignore patterns of empty lines and comments
    ignores = [ign.strip() for ign in ignores \
               if ign.strip() and not ign.strip().startswith('#')]
    
    for ignore in ignores:
        ignore = ignore.strip()
        if not ignore: continue
        
        for pth in glob(path.join(root, ignore)):
            print('Deleting {0}'.format(pth))
            if path.isdir(pth):
                shutil.rmtree(pth)
            else:
                os.remove(pth)


def init(pyver='2.7', upgrade=False, dir='.', apy=False):
    """Create a virtualenv and setup entry points
    
    Poor man's buildout (supports py3k too!). You will need to have virtualenv
    and virtualenv5 installed before running this command.
    
      pyver             -- The Python version to use (eg: 2.7)
      upgrade           -- Should we upgrade installed packages?
      dir               -- Where to create the virtualenv (default: current dir)
      apy               -- Must use ActivePython
      
    TODO: fail with instructive error message when virtualenv/virtualenv5 is
          not installed (use which.py?)
      
    TODO: support installing [extra] requirements as 'setup.py develop' will
          not install them.
          
    Return the virtualenv binary path that was used to create the virtualenv
    """
    py = get_system_python(pyver)
    virtualenv = 'virtualenv5' if pyver[0] == '3' else 'virtualenv'

    # must be ActivePython
    if apy:
        local('{0} -m activestate'.format(py))

    # create virtualenv
    venv_cmd = '{0} --no-site-packages -p {1} {2}'.format(virtualenv, py, dir)
    local(venv_cmd, capture=False)

    # find paths to essential binaries in the created virtualenv
    python_exe = get_script('python', dir)
    ez_exe = get_script('easy_install', dir)
    pip_exe = get_script('pip', dir)
        
    if WIN:
        # Stupid virtualenv exits immediately to console on Windows, leaving
        # it running as a background process.
        print('*** Waiting for the detached process (virtualenv) to finish (50s)')
        print('*** Press Ctrl+C to forcibly continue')
        try:
            time.sleep(50)
        except KeyboardInterrupt:
            pass
        
    # upgrade to latest distribute; virtualenv must have installed an outdated
    # version.
    install('distribute', dir=dir, force_upgrade=True)

    # setup dev environment
    local('{0} setup.py develop'.format(python_exe))
    
    return virtualenv
    
    
def get_script(name, dir='.'):
    """Return the path to the given script in virtualenv"""
    scripts_dir = 'Scripts' if WIN else 'bin'
    return path.join(dir, scripts_dir, name + '.exe' if WIN else name)
    
    
def install(pkg, dir='.', force_upgrade=False):
    """Install the given package into virtualenv
    
    force_upgrade      -- pass -U option to pip/easy_install
    """
    pip_exe = get_script('pip', dir)
    if path.exists(pip_exe):
        install_cmd = '{0} install {1} {{0}}'.format(
            pip_exe, '-U' if force_upgrade else '')
    else:
        # pip exe doesn't exist (python3?); fallback to easy_install.
        
        # Run easy_install via `python -m` to prevent easy_install.exe from
        # opening new command prompts (silly)
        # ez_exe = get_script('easy_install', dir)
        py_exe = get_script('python', dir)
        install_cmd = '{0} -m easy_install {1} {{0}}'.format(
            py_exe, '-U' if force_upgrade else '')
    local(install_cmd.format(pkg))


def get_system_python(pyver):
    """Return the command to run system Python
    
    On Mac, this returns the full path to /Lib../Frm... Python (not /System)
    On Windows, this returns pythonXY.exe (ActivePython)
    On Linux, this simply returns pythonX.Y
    """
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
