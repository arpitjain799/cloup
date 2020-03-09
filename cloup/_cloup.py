from collections import OrderedDict

import click


class OptionGroup:
    def __init__(self, name, help=None, options=[]):
        if not name:
            raise ValueError('name is a mandatory argument')
        self.name = name
        self.help = help
        self.options = list(options)

    def get_help_records(self, ctx):
        return [opt.get_help_record(ctx) for opt in self if not opt.hidden]

    def append(self, option):
        self.options.append(option)

    def __iter__(self):
        return iter(self.options)

    def __getitem__(self, i):
        return self.options[i]

    def __len__(self) -> int:
        return len(self.options)

    def __repr__(self):
        return 'OptionGroup({}, help={}, options={})'.format(
            self.name, self.options, self.help)

    def __str__(self):
        return 'OptionGroup({}, help={}, options={})'.format(
            self.name, [opt.name for opt in self.options], self.help)


class GroupedOption(click.Option):
    """ A click.Option with an extra field ``group`` of type OptionGroup """

    def __init__(self, param_decls=None, show_default=False, prompt=False,
                 confirmation_prompt=False, hide_input=False, is_flag=None, flag_value=None,
                 multiple=False, count=False, allow_from_autoenv=True, type=None, help=None,
                 hidden=False, show_choices=True, show_envvar=False, group=None, **attrs):
        self.group = group
        super().__init__(param_decls, show_default, prompt, confirmation_prompt, hide_input,
                         is_flag, flag_value, multiple, count, allow_from_autoenv, type, help,
                         hidden, show_choices, show_envvar, **attrs)


def has_option_group(param):
    return hasattr(param, 'group') and param.group is not None


def get_option_group_of(param, default=None):
    return param.group if has_option_group(param) else default


class Command(click.Command):
    """ A ``click.Command`` supporting option groups. """

    def __init__(self, name, context_settings=None, callback=None, params=None,
                 help=None, epilog=None, short_help=None, options_metavar='[OPTIONS]',
                 add_help_option=True, hidden=False, deprecated=False):

        super().__init__(name, context_settings, callback, params, help, epilog, short_help,
                         options_metavar, add_help_option, hidden, deprecated)

        options_by_group = OrderedDict()
        for param in self.params:
            if isinstance(param, click.Argument):
                continue
            options_by_group.setdefault(get_option_group_of(param), []).append(param)

        self.ungrouped_options = options_by_group.pop(None, default=[])
        self.option_groups = list(options_by_group.keys())
        for group, options in options_by_group.items():
            group.options = options

    def get_ungrouped_options(self, ctx):
        help_option = self.get_help_option(ctx)
        if help_option is not None:
            return self.ungrouped_options + [help_option]
        else:
            return self.ungrouped_options

    def format_option_group(self, ctx, formatter, option_group):  # noqa
        with formatter.section(option_group.name):
            if option_group.help:
                formatter.write_text(option_group.help)
            help_records = option_group.get_help_records(ctx)
            formatter.write_dl(help_records)

    def format_ungrouped_options(self, ctx, formatter, options):
        default_group = OptionGroup(
            name='Other options' if self.option_groups else 'Options',
            options=options)
        self.format_option_group(ctx, formatter, default_group)

    def format_options(self, ctx, formatter):
        for option_group in self.option_groups:
            self.format_option_group(ctx, formatter, option_group)
        ungrouped_options = self.get_ungrouped_options(ctx)
        if ungrouped_options:
            self.format_ungrouped_options(ctx, formatter, ungrouped_options)


class Group(click.Group):
    """ A ``click.Group`` supporting option groups. """

    def command(self, name=None, cls=Command, **attrs):
        return super().command(name=name, cls=cls, **attrs)

    def group(self, name=None, cls=None, **attrs):
        if cls is None:
            cls = Group
        return super().group(name=name, cls=cls, **attrs)


def group(name=None, cls=Group, **attrs):
    """ Creates a new ``cloup.Group`` (by default). """
    return click.group(name=name, cls=cls, **attrs)


def command(name=None, cls=Command, **attrs):
    """ Creates a new ``cloup.Command`` (by default). """
    return click.command(name, cls=cls, **attrs)


def option(*param_decls, **attrs):
    """ Attaches a ``GroupedOption``, i.e. an option supporting option groups. """

    def decorator(f, group=None):
        return click.option(*param_decls, cls=GroupedOption, group=group, **attrs)(f)

    return decorator


def option_group(name, options, help=None):
    """ Attaches an option group to the command. """
    opt_group = OptionGroup(name, help=help)

    def decorator(f):
        for opt_decorator in reversed(options):
            opt_decorator(f, opt_group)
        return f

    return decorator
