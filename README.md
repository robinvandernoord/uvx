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

## Note - Version 2.0 Now Available

Version `2.0.0` of uvx has been released and is now available. This new release has been rewritten in Rust to address performance concerns with the previous Python implementation, notably reducing startup time. Version `2.0.0` directly utilizes some APIs of `uv`, enhancing performance by avoiding the need to spawn a separate process in some cases. 

Despite the availability of this new version, the repository and the existing Python implementation of uvx 1.x will continue to be maintained for bug fixes and to ensure (backwards) compatibility across different system architectures.

For users on supported Linux platforms with x86_64 (amd64) or aarch64 (ARM64) architectures, version 2.0 can be installed via pip or compiled manually from source if necessary. This version is not available through PyPI for other platforms, which can still utilize uvx 1.x or opt for manual compilation of uvx 2.0.

Discover more about the new features and enhancements by visiting the new project repository at [robinvandernoord/uvx2](https://github.com/robinvandernoord/uvx2/).


## License

`uvx` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## Changelog

See `CHANGELOG.md` [on GitHub](https://github.com/robinvandernoord/uvx/blob/master/CHANGELOG.md)
