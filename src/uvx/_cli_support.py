import functools
import typing

import click
import configuraptor


class State(configuraptor.TypedConfig, configuraptor.Singleton):
    """Global cli app state."""

    verbose: bool = False


###
# https://github.com/educationwarehouse/edwh/blob/caae192e016f5dc4677f404f201f798569d3fcb6/src/edwh/helpers.py#L259
###


KEY_ENTER = "\r"
KEY_ARROWUP = "\033[A"
KEY_ARROWDOWN = "\033[B"

T_Key = typing.TypeVar("T_Key", bound=typing.Hashable)


def print_box(label: str, selected: bool, current: bool, number: int, fmt: str = "[%s]", filler: str = "x") -> None:
    """
    Print a box for interactive selection.

    Helper function for 'interactive_selected_radio_value'.
    """
    box = fmt % (filler if selected else " ")
    indicator = ">" if current else " "
    click.echo(f"{indicator}{number}. {box} {label}")


def interactive_selected_radio_value(
    options: list[str] | dict[T_Key, str],
    prompt: str = "Select an option (use arrow keys, spacebar, or digit keys, press 'Enter' to finish):",
    selected: T_Key | None = None,
) -> str:
    """
    Provide an interactive radio box selection in the console.

    The user can navigate through the options using the arrow keys,
    select an option using the spacebar or digit keys, and finish the selection by pressing 'Enter'.

    Args:
        options: A list or dict (value: label) of options to be displayed as radio boxes.
        prompt (str, optional): A string that is displayed as a prompt for the user.
        selected: a pre-selected option.
            T_Key means the value has to be the same type as the keys of options.
            Example:
                options = {1: "something", "two": "else"}
                selected = 2 # valid type (int is a key of options)
                selected = 1.5 # invalid type (none of the keys of options are a float)

    Returns:
        str: The selected option value.

    Examples:
        interactive_selected_radio_value(["first", "second", "third"])

        interactive_selected_radio_value({100: "first", 211: "second", 355: "third"})

        interactive_selected_radio_value(["first", "second", "third"], selected="third")

        interactive_selected_radio_value({1: "first", 2: "second", 3: "third"}, selected=3)
    """
    selected_index: int | None = None
    current_index = 0

    if isinstance(options, list):
        labels = options
    else:
        labels = list(options.values())
        options = list(options.keys())  # type: ignore

    if selected in options:
        selected_index = current_index = options.index(selected)  # type: ignore

    print_radio_box = functools.partial(print_box, fmt="(%s)", filler="o")

    while True:
        click.clear()
        click.echo(prompt)

        for i, option in enumerate(labels, start=1):
            print_radio_box(option, i - 1 == selected_index, i - 1 == current_index, i)

        key = click.getchar()

        if key == KEY_ENTER:
            if selected_index is None:
                # no you may not leave.
                continue
            else:
                # done!
                break

        elif key == KEY_ARROWUP:  # Up arrow
            current_index = (current_index - 1) % len(options)
        elif key == KEY_ARROWDOWN:  # Down arrow
            current_index = (current_index + 1) % len(options)
        elif key.isdigit() and 1 <= int(key) <= len(options):
            selected_index = int(key) - 1
        elif key == " ":
            selected_index = current_index

    return options[selected_index]
