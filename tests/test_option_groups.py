"""Tests for the "option groups" feature/module."""
from textwrap import dedent

import pytest
from click import pass_context

import cloup
from cloup import OptionGroup, option
from tests.util import make_options, parametrize, noop


@parametrize(
    ['tabular_help', 'align_option_groups'],
    pytest.param(True, True, id='tabular-aligned'),
    pytest.param(True, False, id='tabular-non_aligned'),
    pytest.param(False, None, id='linear'),
)
def test_option_groups_are_correctly_displayed_in_help(
    runner, tabular_help, align_option_groups, get_example_command
):
    cmd = get_example_command(
        tabular_help=tabular_help,
        align_option_groups=align_option_groups
    )
    result = runner.invoke(cmd, args=('--help',))
    assert result.exit_code == 0
    assert result.output.strip() == cmd.expected_help


def test_option_group_constraints_are_checked(runner, get_example_command):
    cmd = get_example_command(align_option_groups=False)

    result = runner.invoke(cmd, args='--one=1')
    assert result.exit_code == 0

    result = runner.invoke(cmd, args='--one=1 --three=3 --five=4')
    assert result.exit_code == 0

    result = runner.invoke(cmd, args='--one=1 --three=3')
    assert result.exit_code == 2
    error_prefix = ('Error: when --three is set, at least 1 of the following '
                    'parameters must be set')
    assert error_prefix in result.output


def test_option_group_decorator_raises_if_group_is_passed_to_contained_option():
    func = cloup.option_group(
        'a group', cloup.option('--opt', group=cloup.OptionGroup('another group')))
    with pytest.raises(ValueError):
        func(noop)


def test_option_group_decorator_raises_for_no_options():
    with pytest.raises(ValueError):
        cloup.option_group('grp')


@pytest.mark.parametrize(['ctx_value', 'cmd_value', 'should_align'], [
    pytest.param(True, None, True, id='ctx-yes'),
    pytest.param(False, None, False, id='ctx-no'),
    pytest.param(False, True, True, id='none'),
    pytest.param(True, False, False, id='ctx-yes_cmd-no'),
    pytest.param(False, True, True, id='ctx-no_cmd-yes'),
])
def test_align_option_groups_context_setting(runner, ctx_value, cmd_value, should_align):
    @cloup.command(
        context_settings=dict(align_option_groups=ctx_value),
        align_option_groups=cmd_value,
    )
    @cloup.option_group('First group', option('--opt', help='first option'))
    @cloup.option_group('Second group', option('--much-longer-opt', help='second option'))
    @pass_context
    def cmd(ctx, one, much_longer_opt):
        assert cmd.must_align_groups(ctx) == should_align

    result = runner.invoke(cmd, args=('--help',))
    start = result.output.find('First')
    if should_align:
        expected = """
            First group:
              --opt TEXT              first option

            Second group:
              --much-longer-opt TEXT  second option

            Other options:
              --help                  Show this message and exit."""
    else:
        expected = """
            First group:
              --opt TEXT  first option

            Second group:
              --much-longer-opt TEXT  second option

            Other options:
              --help  Show this message and exit."""

    expected = dedent(expected).strip()
    end = start + len(expected)
    assert result.output[start:end] == expected


def test_context_settings_propagate_to_children(runner):
    @cloup.group(context_settings=dict(align_option_groups=False))
    def grp():
        pass

    @grp.command()
    @pass_context
    def cmd(ctx):
        assert cmd.must_align_option_groups(ctx) is False

    runner.invoke(grp, ('cmd',))


def test_that_neither_optgroup_nor_its_options_are_shown_if_optgroup_is_hidden(runner):
    @cloup.command('name')
    @cloup.option_group(
        'Hidden group',
        cloup.option('--one'),
        hidden=True
    )
    def cmd():
        pass

    result = runner.invoke(cmd, args=('--help',), catch_exceptions=False)
    assert 'Hidden group' not in result.output
    assert '--one' not in result.output


def test_that_optgroup_is_hidden_if_all_its_options_are_hidden(runner):
    @cloup.command('name')
    @cloup.option_group(
        'Hidden group',
        cloup.option('--one', hidden=True),
        cloup.option('--two', hidden=True),
    )
    def cmd():
        pass

    assert cmd.option_groups[0].hidden
    result = runner.invoke(cmd, args=('--help',), catch_exceptions=False)
    assert 'Hidden group' not in result.output


def test_option_group_options_setter_set_the_hidden_attr_of_options():
    opts = make_options('abc')
    group = OptionGroup('name')
    group.options = opts
    assert not any(opt.hidden for opt in opts)
    group.hidden = True
    group.options = opts
    assert all(opt.hidden for opt in opts)
