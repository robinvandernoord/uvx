# uvx (DEPRECATED)

**Note: The `uvx` project has been deprecated as of version 3.0. Development has moved to [`uvenv`](https://github.com/robinvandernoord/uvenv).**

The name change was necessary due to a conflict with Astral's `uvx` CLI command (`uv tool run`).

If you are looking for an updated and maintained version of this tool, please visit the [`uvenv`](https://github.com/robinvandernoord/uvenv) repository.

## Legacy Versions

- `uvx` versions up to `2.x` will remain available for historical purposes and limited maintenance.
- No new features or updates will be added to this repository beyond critical bug fixes.

## Migration to uvenv

To upgrade to `uvenv`, use one of the following installation methods:

```bash
#
# migrate:
uvx self-update # will install uvenv automatically 
uvenv self migrate # will migrate your packages

# Or install uvenv fresh:
pip install uvenv # or uv install, pipx install
```
