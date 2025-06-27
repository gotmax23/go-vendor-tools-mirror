# Copyright (C) 2025 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import sys
from textwrap import dedent, indent


def format_choices(*choices: object):
    result = ""
    length = len(choices)
    for idx, choice in enumerate(choices):
        result += f"`{choice}`"
        if idx < length - 1:
            result += ", "
    return result


def head_factory(initial_indent_level: int):
    return lambda level=1: "#" * (initial_indent_level + level)


def format_subparsers(
    parser: argparse.ArgumentParser, initial_indent_level: int
) -> list[str]:
    head = head_factory(initial_indent_level)
    lines: list[str] = []
    subparsers_action: argparse._SubParsersAction
    if not parser._subparsers:
        return lines
    for action in reversed(parser._subparsers._actions):
        if isinstance(action, argparse._SubParsersAction):
            subparsers_action = action
            break
    else:
        return lines
    lines.append(f"\n{head(1)} Subcommands")
    for subparser in subparsers_action.choices.values():
        if "internal" in (subparser.description or "").lower():
            continue
        lines.append("")
        lines.extend(format_command(subparser, initial_indent_level + 1))
    return lines


def _process_actions(
    actions: list[argparse.Action],
) -> tuple[list[argparse.Action], list[argparse.Action]]:
    """
    Returns: (regular actions, positional arg actions)
    """
    options: list[argparse.Action] = []
    positionals: list[argparse.Action] = []
    for action in actions:
        if isinstance(action, argparse._SubParsersAction):
            continue
        if action.option_strings:
            options.append(action)
        else:
            assert action.dest
            positionals.append(action)
    return options, positionals


def _format_action(action: argparse.Action) -> list[str]:
    lines: list[str] = []
    if action.option_strings:
        # Option
        opts = [f"`{opt}`" for opt in action.option_strings]
        line = "- " + ",".join(opts)
        if action.metavar:
            line += f" `{action.metavar}`"
    else:
        metavar = action.metavar or action.dest
        line = f"- `{metavar}`"
    if action.help:
        action_vars = vars(action).copy()
        if action_vars.get("choices"):
            action_vars["choices"] = format_choices(*action_vars["choices"])
        help_msg = dedent(action.help)
        help_msg = help_msg % action_vars
        if help_msg.startswith("\n"):
            lines.append(line + ":")
            line = indent(help_msg, " " * 4)
        else:
            line += f": {help_msg}"
    lines.append(line)
    return lines


def _format_actions(actions: list[argparse.Action]) -> list[str]:
    lines: list[str] = []
    for action in actions:
        lines.extend(_format_action(action))
    return lines


def format_all_actions(
    actions: list[argparse.Action], initial_indent_level: int
) -> list[str]:
    head = head_factory(initial_indent_level)
    lines: list[str] = []
    options, positionals = _process_actions(actions)
    if positionals:
        lines.append(f"\n{head()} Positionals\n")
        lines.extend(_format_actions(positionals))
    if options:
        lines.append(f"\n{head()} Options\n")
        lines.extend(_format_actions(options))
    return lines


def format_command(
    parser: argparse.ArgumentParser,
    initial_indent_level: int = 0,
) -> list[str]:
    head = head_factory(initial_indent_level)

    lines = []
    lines.append(f"{head()} {parser.prog}")
    if parser.description:
        lines.append(f"\n{head(2)} Description\n")
        lines.append(parser.description)
    lines.append(f"\n{head(2)} Usage\n")
    lines.append("``` text")
    lines.append(parser.format_usage().strip("\n").removeprefix("usage: "))
    lines.append("```")
    lines.extend(format_all_actions(parser._actions, initial_indent_level + 1))
    lines.extend(format_subparsers(parser, initial_indent_level + 1))
    return lines


def get_lines(refresh: bool = False) -> list[str]:
    """
    Args:
        refresh:
            When this is run with mkdocs serve, it is necessary to reload the
            module to ensure the latest version of get_parser is used.
    """
    if refresh:
        sys.modules.pop("go_vendor_tools.cli.go_vendor_license", None)
    from go_vendor_tools.cli.go_vendor_license import get_parser  # noqa: PLC0415

    parser = get_parser()
    return format_command(parser)


def main() -> None:
    print("\n".join(get_lines()))


if __name__ == "__main__":
    main()
