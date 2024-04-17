# uvx: pipx for uv

Inspired by:

- [pipx](https://github.com/pypa/pipx)
- [uv](https://github.com/astral-sh/uv)

## Installation

```bash
# one of these ways:
pip install uvx
uv install uvx
pipx install uvx
```

## Usage

```bash
uvx
```

Run `uvx` without any arguments to see all possible subcommands.

## Note - pending replacement

Although version `1.0.0` was recently released, work has already begun on version `2.0.0`, which is being developed
at [robinvandernoord/uvx2](https://github.com/robinvandernoord/uvx2/). The decision to undertake this new version is
driven by performance concerns with the current Python implementation, which has a startup time of 200ms. To address
this, `uvx 2.0` is being rewritten in Rust. This transition will enable `uvx` to utilize some of the APIs of `uv`
directly, without the need to spawn a separate process (in some cases), thus enhancing performance further. 
Despite this rewrite, both the repository and the existing Python implementation will be maintained, 
particularly for bug fixes, because it may have a larger (backwards) compatibility across system architectures.

## License

`uvx` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## Changelog

See `CHANGELOG.md` [on GitHub](https://github.com/robinvandernoord/uvx/blob/master/CHANGELOG.md)