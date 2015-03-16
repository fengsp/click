"""
    click._termui_impl
    ~~~~~~~~~~~~~~~~~~

    This module contains implementations for the termui module.  To keep the
    import time of Click down, some infrequently used functionality is placed
    in this module and only imported as needed.

    :copyright: (c) 2014 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import os
import sys
import time
import math
from ._compat import _default_text_stdout, range_type, PY2, isatty, \
     open_stream, strip_ansi, term_len, get_best_encoding, WIN
from .utils import echo
from .exceptions import ClickException


class Editor(object):

    def edit(self, text):
        import tempfile

        text = text or ''
        if text and not text.endswith('\n'):
            text += '\n'

        fd, name = tempfile.mkstemp(prefix='editor-', suffix=self.extension)
        try:
            if WIN:
                encoding = 'utf-8-sig'
                text = text.replace('\n', '\r\n')
            else:
                encoding = 'utf-8'
            text = text.encode(encoding)

            f = os.fdopen(fd, 'wb')
            f.write(text)
            f.close()
            timestamp = os.path.getmtime(name)

            self.edit_file(name)

            if self.require_save \
               and os.path.getmtime(name) == timestamp:
                return None

            f = open(name, 'rb')
            try:
                rv = f.read()
            finally:
                f.close()
            return rv.decode('utf-8-sig').replace('\r\n', '\n')
        finally:
            os.unlink(name)


def open_url(url, wait=False, locate=False):
    import subprocess

    def _unquote_file(url):
        try:
            import urllib
        except ImportError:
            import urllib
        if url.startswith('file://'):
            url = urllib.unquote(url[7:])
        return url

    if sys.platform == 'darwin':
        args = ['open']
        if wait:
            args.append('-W')
        if locate:
            args.append('-R')
        args.append(_unquote_file(url))
        null = open('/dev/null', 'w')
        try:
            return subprocess.Popen(args, stderr=null).wait()
        finally:
            null.close()
    elif WIN:
        if locate:
            url = _unquote_file(url)
            args = 'explorer /select,"%s"' % _unquote_file(
                url.replace('"', ''))
        else:
            args = 'start %s "" "%s"' % (
                wait and '/WAIT' or '', url.replace('"', ''))
        return os.system(args)

    try:
        if locate:
            url = os.path.dirname(_unquote_file(url)) or '.'
        else:
            url = _unquote_file(url)
        c = subprocess.Popen(['xdg-open', url])
        if wait:
            return c.wait()
        return 0
    except OSError:
        if url.startswith(('http://', 'https://')) and not locate and not wait:
            import webbrowser
            webbrowser.open(url)
            return 0
        return 1


def _translate_ch_to_exc(ch):
    if ch == '\x03':
        raise KeyboardInterrupt()
    if ch == '\x04':
        raise EOFError()


if WIN:
    import msvcrt

    def getchar(echo):
        rv = msvcrt.getch()
        if echo:
            msvcrt.putchar(rv)
        _translate_ch_to_exc(rv)
        if PY2:
            enc = getattr(sys.stdin, 'encoding', None)
            if enc is not None:
                rv = rv.decode(enc, 'replace')
            else:
                rv = rv.decode('cp1252', 'replace')
        return rv
else:
    import tty
    import termios

    def getchar(echo):
        if not isatty(sys.stdin):
            f = open('/dev/tty')
            fd = f.fileno()
        else:
            fd = sys.stdin.fileno()
            f = None
        try:
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = os.read(fd, 32)
                if echo and isatty(sys.stdout):
                    sys.stdout.write(ch)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                sys.stdout.flush()
                if f is not None:
                    f.close()
        except termios.error:
            pass
        _translate_ch_to_exc(ch)
        return ch.decode(get_best_encoding(sys.stdin), 'replace')
