import os
import sys
from collections import deque

from ._compat import text_type, open_stream, get_streerror, string_types, \
     PY2, binary_streams, text_streams, filename_to_ui, \
     auto_wrap_for_ansi, strip_ansi, should_strip_ansi, \
     _default_text_stdout, _default_text_stderr, is_bytes, WIN

if not PY2:
    from ._compat import _find_binary_writer


echo_native_types = string_types + (bytes, bytearray)


def _posixify(name):
    return '-'.join(name.split()).lower()


def make_default_short_help(help, max_length=45):
    words = help.split()
    total_length = 0
    result = []
    done = False

    for word in words:
        if word[-1:] == '.':
            done = True
        new_length = result and 1 + len(word) or len(word)
        if total_length + new_length > max_length:
            result.append('...')
            done = True
        else:
            if result:
                result.append(' ')
            result.append(word)
        if done:
            break
        total_length += new_length

    return ''.join(result)
