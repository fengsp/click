from contextlib import contextmanager
from .termui import get_terminal_size
from .parser import split_opt
from ._compat import term_len


def measure_table(rows):
    widths = {}
    for row in rows:
        for idx, col in enumerate(row):
            widths[idx] = max(widths.get(idx, 0), term_len(col))
    return tuple(y for x, y in sorted(widths.items()))


def iter_rows(rows, col_count):
    for row in rows:
        row = tuple(row)
        yield row + ('',) * (col_count - len(row))


class HelpFormatter(object):
    def write_dl(self, rows, col_max=30, col_spacing=2):
        """Writes a definition list into the buffer.  This is how options
        and commands are usually formatted.

        :param rows: a list of two item tuples for the terms and values.
        :param col_max: the maximum width of the first column.
        :param col_spacing: the number of spaces between the first and
                            second column.
        """
        rows = list(rows)
        widths = measure_table(rows)
        if len(widths) != 2:
            raise TypeError('Expected two columns for definition list')

        first_col = min(widths[0], col_max) + col_spacing

        for first, second in iter_rows(rows, len(widths)):
            self.write('%*s%s' % (self.current_indent, '', first))
            if not second:
                self.write('\n')
                continue
            if term_len(first) <= first_col - col_spacing:
                self.write(' ' * (first_col - term_len(first)))
            else:
                self.write('\n')
                self.write(' ' * (first_col + self.current_indent))

            text_width = max(self.width - first_col - 2, 10)
            lines = iter(wrap_text(second, text_width).splitlines())
            if lines:
                self.write(next(lines) + '\n')
                for line in lines:
                    self.write('%*s%s\n' % (
                        first_col + self.current_indent, '', line))
            else:
                self.write('\n')


def join_options(options):
    """Given a list of option strings this joins them in the most appropriate
    way and returns them in the form ``(formatted_string,
    any_prefix_is_slash)`` where the second item in the tuple is a flag that
    indicates if any of the option prefixes was a slash.
    """
    rv = []
    any_prefix_is_slash = False
    for opt in options:
        prefix = split_opt(opt)[0]
        if prefix == '/':
            any_prefix_is_slash = True
        rv.append((len(prefix), opt))

    rv.sort(key=lambda x: x[0])

    rv = ', '.join(x[1] for x in rv)
    return rv, any_prefix_is_slash
