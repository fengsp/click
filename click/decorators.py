import sys
import inspect

from functools import update_wrapper

from ._compat import iteritems
from .utils import echo


def pass_context(f):
    """Marks a callback as wanting to receive the current context
    object as first argument.
    """
    f.__click_pass_context__ = True
    return f


def pass_obj(f):
    """Similar to :func:`pass_context`, but only pass the object on the
    context onwards (:attr:`Context.obj`).  This is useful if that object
    represents the state of a nested system.
    """
    @pass_context
    def new_func(*args, **kwargs):
        ctx = args[0]
        return ctx.invoke(f, ctx.obj, *args[1:], **kwargs)
    return update_wrapper(new_func, f)


def make_pass_decorator(object_type, ensure=False):
    """Given an object type this creates a decorator that will work
    similar to :func:`pass_obj` but instead of passing the object of the
    current context, it will find the innermost context of type
    :func:`object_type`.

    This generates a decorator that works roughly like this::

        from functools import update_wrapper

        def decorator(f):
            @pass_context
            def new_func(ctx, *args, **kwargs):
                obj = ctx.find_object(object_type)
                return ctx.invoke(f, obj, *args, **kwargs)
            return update_wrapper(new_func, f)
        return decorator

    :param object_type: the type of the object to pass.
    :param ensure: if set to `True`, a new object will be created and
                   remembered on the context if it's not there yet.
    """
    def decorator(f):
        @pass_context
        def new_func(*args, **kwargs):
            ctx = args[0]
            if ensure:
                obj = ctx.ensure_object(object_type)
            else:
                obj = ctx.find_object(object_type)
            if obj is None:
                raise RuntimeError('Managed to invoke callback without a '
                                   'context object of type %r existing'
                                   % object_type.__name__)
            return ctx.invoke(f, obj, *args[1:], **kwargs)
        return update_wrapper(new_func, f)
    return decorator


def confirmation_option(*param_decls, **attrs):
    """Shortcut for confirmation prompts that can be ignored by passing
    ``--yes`` as parameter.

    This is equivalent to decorating a function with :func:`option` with
    the following parameters::

        def callback(ctx, param, value):
            if not value:
                ctx.abort()

        @click.command()
        @click.option('--yes', is_flag=True, callback=callback,
                      expose_value=False, prompt='Do you want to continue?')
        def dropdb():
            pass
    """
    def decorator(f):
        def callback(ctx, param, value):
            if not value:
                ctx.abort()
        attrs.setdefault('is_flag', True)
        attrs.setdefault('callback', callback)
        attrs.setdefault('expose_value', False)
        attrs.setdefault('prompt', 'Do you want to continue?')
        attrs.setdefault('help', 'Confirm the action without prompting.')
        return option(*(param_decls or ('--yes',)), **attrs)(f)
    return decorator


def password_option(*param_decls, **attrs):
    """Shortcut for password prompts.

    This is equivalent to decorating a function with :func:`option` with
    the following parameters::

        @click.command()
        @click.option('--password', prompt=True, confirmation_prompt=True,
                      hide_input=True)
        def changeadmin(password):
            pass
    """
    def decorator(f):
        attrs.setdefault('prompt', True)
        attrs.setdefault('confirmation_prompt', True)
        attrs.setdefault('hide_input', True)
        return option(*(param_decls or ('--password',)), **attrs)(f)
    return decorator


def version_option(version=None, *param_decls, **attrs):
    """Adds a ``--version`` option which immediately ends the program
    printing out the version number.  This is implemented as an eager
    option that prints the version and exits the program in the callback.

    :param version: the version number to show.  If not provided Click
                    attempts an auto discovery via setuptools.
    :param prog_name: the name of the program (defaults to autodetection)
    :param message: custom message to show instead of the default
                    (``'%(prog)s, version %(version)s'``)
    :param others: everything else is forwarded to :func:`option`.
    """
    if version is None:
        module = sys._getframe(1).f_globals.get('__name__')
    def decorator(f):
        prog_name = attrs.pop('prog_name', None)
        message = attrs.pop('message', '%(prog)s, version %(version)s')

        def callback(ctx, param, value):
            if not value or ctx.resilient_parsing:
                return
            prog = prog_name
            if prog is None:
                prog = ctx.find_root().info_name
            ver = version
            if ver is None:
                try:
                    import pkg_resources
                except ImportError:
                    pass
                else:
                    for dist in pkg_resources.working_set:
                        scripts = dist.get_entry_map().get('console_scripts') or {}
                        for script_name, entry_point in iteritems(scripts):
                            if entry_point.module_name == module:
                                ver = dist.version
                                break
                if ver is None:
                    raise RuntimeError('Could not determine version')
            echo(message % {
                'prog': prog,
                'version': ver,
            }, color=ctx.color)
            ctx.exit()

        attrs.setdefault('is_flag', True)
        attrs.setdefault('expose_value', False)
        attrs.setdefault('is_eager', True)
        attrs.setdefault('help', 'Show the version and exit.')
        attrs['callback'] = callback
        return option(*(param_decls or ('--version',)), **attrs)(f)
    return decorator


def help_option(*param_decls, **attrs):
    """Adds a ``--help`` option which immediately ends the program
    printing out the help page.  This is usually unnecessary to add as
    this is added by default to all commands unless suppressed.

    Like :func:`version_option`, this is implemented as eager option that
    prints in the callback and exits.

    All arguments are forwarded to :func:`option`.
    """
    def decorator(f):
        def callback(ctx, param, value):
            if value and not ctx.resilient_parsing:
                echo(ctx.get_help(), color=ctx.color)
                ctx.exit()
        attrs.setdefault('is_flag', True)
        attrs.setdefault('expose_value', False)
        attrs.setdefault('help', 'Show this message and exit.')
        attrs.setdefault('is_eager', True)
        attrs['callback'] = callback
        return option(*(param_decls or ('--help',)), **attrs)(f)
    return decorator


# Circular dependencies between core and decorators
from .core import Command, Group, Argument, Option
