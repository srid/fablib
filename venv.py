# Copyright (c) 2010 ActiveState Software Inc. All rights reserved.

"""Virtualenv utilities for fabric"""

import os
from os import path
from glob import glob
import sys
import shutil
import time
import subprocess
import urllib
from contextlib import contextmanager


# Make this module fabric-independent
try:
    from fabric.api import local as _local
    # Holy cow! Fabric errors won't show stdout/stderr
    # http://stackoverflow.com/questions/1875306
    def local(cmd, capture=False):
        return _local(cmd, capture)
except IOError:
    def local(cmd, capture=False):
        """A clone of fabric.api.local() using ``subprocess``"""
        if capture:
            return subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.PIPE).communicate()[0]
        else:
            subprocess.Popen(cmd, shell=True).communicate()[0]


WIN = sys.platform == 'win32'


def clean():
    """Delete all files/directories ignored in source control
    
    The following source control systems are supported:
    
      svn --    svn:ignore
      
    The idea is to eventually to delete virtualenv-created files to start
    from scratch.
    """
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
    virtualenv = create_virtualenv(pyver, dir, apy)

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
    if path.exists('setup.py'):
        local('{0} setup.py develop'.format(python_exe))
    else:
        print('No setup.py found; not installing dependencies')
    
    return virtualenv


def create_virtualenv(pyver, dir, apy=False):
    """Keep this function independent of fabric"""
    py = get_system_python(pyver)
    if pyver[0] == '3':
        virtualenv = 'virtualenv5'
        distribute_option = ''  # not required
    else:
        virtualenv = 'virtualenv'
        distribute_option = '--distribute'

    # must be ActivePython
    if apy:
        local('{0} -m activestate'.format(py))

    # create virtualenv
    with _workaround_virtualenv_bugs(py, dir):
        venv_cmd = '{0} --no-site-packages {1} -p {2} {3}'.format(
            virtualenv, distribute_option, py, dir)
        local(venv_cmd)
        
    return virtualenv
    
    
def get_script(name, dir='.'):
    """Return the path to the given script in virtualenv"""
    scripts_dir = 'Scripts' if WIN else 'bin'
    return path.join(dir, scripts_dir, name + '.exe' if WIN else name)
    
    
def install(pkg, dir='.', force_upgrade=False):
    """Install the given package into virtualenv
    
    force_upgrade      -- pass -U option to pip/easy_install
    
    Installers are detected in this order:
        PyPM           (on PATH)
        pip            (on scripts/)
        easy_install   (on scripts/)
    """
    pypm_exe = get_pypm_script()
    pip_exe = get_script('pip', dir)
    if pypm_exe is not None:
        install_cmd = _pypm_install_cmd(pypm_exe, dir, pkg)
    elif path.exists(pip_exe):
        install_cmd = _pip_install_cmd(pip_exe, pkg, force_upgrade)
    else:
        # pip exe doesn't exist (python3?); fallback to easy_install.
        py_exe = get_script('python', dir)
        install_cmd = _ez_install_cmd(py_exe, pkg, force_upgrade)
    local(install_cmd)


def tox(config='tox.ini'):
    """Run tox -- test across multiple Python versions

    tox will automatically be downloaded, if needed.

    This method also works around virtualenv bugs
    """
    with _workaround_virtualenv_bug_readline():
        # if _in_path('tox'):
        if False:  # disable; may have outdated tox installed.
            local('tox -v -c %s' % config)
        else:
            # http://codespeak.net/tox/example/hudson.html#zero-installation-for-slaves
            url = "https://pytox.googlecode.com/hg/toxbootstrap.py"
            d = dict(__filqe__='toxbootstrap.py')
            exec urllib.urlopen(url).read() in d
            d['cmdline'](['--recreate', '-v', '-c', config])
    

def _pypm_install_cmd(pypm, dir, pkg):
    return '{0} --force -E {1} install {2}'.format(pypm, dir, pkg)
    

def _pip_install_cmd(pip_exe, pkg, force_upgrade):
    return '{0} install {1} {2}'.format(
        pip_exe, '-U' if force_upgrade else '', pkg)
    
    
def _ez_install_cmd(py_exe, pkg, force_upgrade):
    # Run easy_install via `python -m` to prevent easy_install.exe from
    # opening new command prompts (silly)
    # ez_exe = get_script('easy_install', dir)
    return '{0} -m easy_install {1} {2}'.format(
        py_exe, '-U' if force_upgrade else '', pkg)


_pypm = ''
def get_pypm_script():
    """Return the command to run PyPM"""
    global _pypm
    if _pypm == '':
        try:
            subprocess.check_call(['pypm', 'info'], stdout=subprocess.PIPE)
            _pypm = 'pypm'
        except subprocess.CalledProcessError:
            _pypm = None
        except OSError as e:
            if e.errno == 2:  # No such file or directory
                _pypm = None
            else:
                raise
        
    return _pypm


def get_system_python(pyver):
    """Return the command to run system Python
    
    On Mac, this returns the full path to /Lib../Frm... Python (not /System)
    On Windows, this returns pythonXY.exe (ActivePython)
    On Linux, this simply returns pythonX.Y
    """
    if sys.platform == 'win32':
        # TODO: support non-ActivePython as well
        python = 'python{pyver[0]}.{pyver[2]}.exe'.format(pyver=pyver)
    elif sys.platform == 'darwin':
        python = '/Library/Frameworks/Python.framework/Versions/{pyver}/bin/python{pyver}'.format(
            pyver=pyver)
    else:
        python = 'python' + pyver

    return python

def _in_path(prog):
    """Return True of `prog` is in PATH"""
    if sys.platform == 'win32':
        exts = ('.exe', '.bat', '.cmd')
        for p in os.environ['PATH'].split(';'):
            for ext in exts:
                if P.exists(P.join(p, prog + ext)):
                    return True
    else:
        for p in os.environ['PATH'].split(':'):
            if P.exists(P.join(p, prog)):
                return True
    return False


@contextmanager
def _workaround_virtualenv_bugs(py, dir):
    """Patch the way the virtualenv works, specifically:
    
    a) Move user readline.so out of the way
       http://bitbucket.org/ianb/virtualenv/issue/64
       
    b) Include PyWin32 in global site-packages
    """
    if sys.platform == 'win32':
        with _workaround_virtualenv_bug_pywin32(py, dir):
            yield
    else:
        with _workaround_virtualenv_bug_readline():
            yield
    

@contextmanager
def _workaround_virtualenv_bug_readline():
    # a) Move readline.so out of the way
    if sys.platform != 'win32':
        readline_canditates = [
            '~/.local/lib/python?.?/site-packages/readline.so',
            '~/Library/Python/?.?/lib/python/site-packages/readline.so',
        ]
        readlines = []
        for c in readline_canditates:
            readlines.extend(glob(path.expanduser(c)))
            
        if readlines:
            print('Moving the following out of the way; virtualenv bug #64')
            print(readlines)
            for rl in readlines:
                os.rename(rl, rl + '.oow')
        try:
            yield
        finally:
            if readlines:
                print('Moving the following back; virtualenv bug #64')
                print(readlines)
                for rl in readlines:
                    os.rename(rl + '.oow', rl)
    else:
        yield


@contextmanager
def _workaround_virtualenv_bug_pywin32(py, dir):
    """It is not a "bug" per se - but a feature!"""
    if sys.platform == 'win32':
        # Include pywin32.pth with absolute filenames
        yield
        get_sp = "import distutils.sysconfig as sc; print(sc.get_python_lib())"
        sp = check_output([py, '-c', get_sp]).strip()
        pthfile = path.join(sp, 'pywin32.pth')
        venv_sp = path.join(dir, 'Lib', 'site-packages')
        if path.exists(pthfile):
            target = path.join(venv_sp, 'pywin32.pth')
            print('Including global PyWin32 package: %s' % target)
            shutil.copyfile(pthfile, target)
            # Make the path absolute
            new_pth = []
            for line in open(target, 'r').readlines():
                if line.strip() and not line.startswith('#'):
                    new_pth.append(path.join(sp, line))
                else:
                    new_pth.append(line)
            with open(target, 'w') as f:
                f.writelines(new_pth)
            print('Patched pywin32.pth')
            
        # But this doesn't make win32com, etc. available in sys.path; we
        # should copy them.
        for source in glob(path.join(sp, 'win32*')):
            target = path.join(venv_sp, path.basename(source))
            print('cp %s -> %s' % (source, target))
            if path.isfile(source):
                shutil.copyfile(source, target)
            else:
                shutil.copytree(source, target)
    else:
        yield
        


# check_output for python2.6
def check_output(*popenargs, **kwargs):
    r"""Run command with arguments and return its output as a byte string.

    If the exit code was non-zero it raises a CalledProcessError.  The
    CalledProcessError object will have the return code in the returncode
    attribute and output in the output attribute.

    The arguments are the same as for the Popen constructor.  Example:

    >>> check_output(["ls", "-l", "/dev/null"])
    'crw-rw-rw- 1 root root 1, 3 Oct 18  2007 /dev/null\n'

    The stdout argument is not allowed as it is used internally.
    To capture standard error in the result, use stderr=STDOUT.

    >>> check_output(["/bin/sh", "-c",
    ...               "ls -l non_existent_file ; exit 0"],
    ...              stderr=STDOUT)
    'ls: non_existent_file: No such file or directory\n'
    """
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise subprocess.CalledProcessError(retcode, cmd, output=output)
    return output


