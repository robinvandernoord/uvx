# Changelog

<!--next-version-placeholder-->

## v1.0.1 (2024-04-26)

### Fix

* **self-update:** Prevent unsupported systems trying to upgrade to uvx 2.x ([`c3862f9`](https://github.com/robinvandernoord/uvx/commit/c3862f9e610779ed36a0ccb648e80c78b1003469))

### Documentation

* Mentioned uvx2 rust rewrite ([`dce1cbb`](https://github.com/robinvandernoord/uvx/commit/dce1cbbf86954948ea9b92db75234861a2d7f7f2))

## v1.0.0 (2024-04-17)

### Feature

* `uvx run <library>` to run a package from pypi ([`faba096`](https://github.com/robinvandernoord/uvx/commit/faba096266f22d668e5a69a381b3b97b6fcad07e))
* **uninject:** Implemented eject ([`fbd2f6e`](https://github.com/robinvandernoord/uvx/commit/fbd2f6efb9a28ec91add88f7afd24bcc58f9ddac))
* Work in progress on more commadns (uninstall-all, reinstall-all, uninject/eject) ([`a0e205c`](https://github.com/robinvandernoord/uvx/commit/a0e205c842a6ea1db2d2f138350b65dce54a6df5))

### Fix

* **upgrade:** Actually listen to 'no_cache' ([`ce7899e`](https://github.com/robinvandernoord/uvx/commit/ce7899e17f357897ebc503d9b8b97b88473f2578))

## v0.9.4 (2024-04-10)

### Fix

* Added icons to self-update, included new TODO ([`637b21b`](https://github.com/robinvandernoord/uvx/commit/637b21b5c859848fa62ef4dabbdc38834b51b555))

## v0.9.3 (2024-04-10)

### Fix

* NOOP patch to test self-update

## v0.9.2 (2024-04-10)

### Fix

* **self-update:** Proper order of old and new + disable caching for self update ([`27298eb`](https://github.com/robinvandernoord/uvx/commit/27298ebfee768c163b6b63db84bd0e5af1fb4f4b))

## v0.9.1 (2024-04-10)

### Fix

* NOOP patch to test self-update

## v0.9.0 (2024-04-10)

### Feature

* Added `uvx self-update` ([`986c7b5`](https://github.com/robinvandernoord/uvx/commit/986c7b55fda215ff877e256e5c88b2f4c3882245))

## v0.8.0 (2024-04-10)

### Feature

* Added `--verbose` flag to global state (+ used by --verbose) ([`8c20be4`](https://github.com/robinvandernoord/uvx/commit/8c20be4c82a8ecd8abe9d7e8615c3da28304c8b4))

### Fix

* Work in progress on `self-update` ([`56dec48`](https://github.com/robinvandernoord/uvx/commit/56dec48a0abb7b32efab5e4e10a034e383b36eb9))

## v0.7.0 (2024-04-10)

### Feature

* `uvx upgrade-all` ([`5edc7af`](https://github.com/robinvandernoord/uvx/commit/5edc7afeda4bb544b346f962a730f66c6b92dbf8))

### Fix

* Make linters etc happy ([`bc16251`](https://github.com/robinvandernoord/uvx/commit/bc16251ac58221131f1192ea78fc95f80650421f))

## v0.6.0 (2024-04-05)

### Feature

* Implemented  first version of `uvx upgrade` ([`ffcb73a`](https://github.com/robinvandernoord/uvx/commit/ffcb73ad928f089ef3c0c3705b00fc04c840c9ff))
* Work in progress on uvx upgrade ([`d48524a`](https://github.com/robinvandernoord/uvx/commit/d48524adf5a9a08ae4d4b8485789ff33e937f278))

## v0.5.2 (2024-03-19)

### Fix

* Exclude these files from pip build ([`0899653`](https://github.com/robinvandernoord/uvx/commit/08996536a64b78680d2cf8e452ee3e871a610464))

## v0.5.1 (2024-03-19)

### Fix

* Include --no-cache for (re)install ([`8ab4de9`](https://github.com/robinvandernoord/uvx/commit/8ab4de9487d7eac7e68632805c8b42190bc2c0a5))

## v0.5.0 (2024-03-19)

### Feature

* Continued `inject` cli functionality ([`ffd3792`](https://github.com/robinvandernoord/uvx/commit/ffd37920eec3f73afe5c2456904cfe590c004615))
* Started on 'inject' ([`7af0558`](https://github.com/robinvandernoord/uvx/commit/7af05585ddf711217a8213013cbcb67c4caa0f00))
* Prepare for 'inject' ([`bd07b9a`](https://github.com/robinvandernoord/uvx/commit/bd07b9a15f278bda0bed119bfe7bb4fec8e60b32))
* Started with `uvx upgrade` ([`2d68e14`](https://github.com/robinvandernoord/uvx/commit/2d68e14e5677ffcaf8ce1db6ebfa55d00dd0077f))

### Fix

* **reinstall:** Still include injected ([`80cfb18`](https://github.com/robinvandernoord/uvx/commit/80cfb1865b6de9c4b34b9eae3eb627136431858a))
* Make local install work again ([`945edf7`](https://github.com/robinvandernoord/uvx/commit/945edf7d3e7e5b996596c891871b9e9816e2151a))
* **json:** Indent json with 2 ([`ce55dd0`](https://github.com/robinvandernoord/uvx/commit/ce55dd01e1003d0f370d66c27177cfbf33f1bb98))
* Metadata to msgpack, allow local install ([`1880062`](https://github.com/robinvandernoord/uvx/commit/18800624ddeeb80946f6022f065628909a8d0a3e))
* Improvements in uv binary detection (right venv) ([`e874d3f`](https://github.com/robinvandernoord/uvx/commit/e874d3fbfa9703c9f0c7b2f500e0e78bddb4b9ce))
* (WIP) try to resolve local packages by dry-run installing them ([`2f2a780`](https://github.com/robinvandernoord/uvx/commit/2f2a78056659cf8c6dcfd287917251e0afcf2431))

## v0.4.1 (2024-03-04)

### Fix

* Always access 'uv' via sys.executable so it won't be missing ([`693708e`](https://github.com/robinvandernoord/uvx/commit/693708ed9a9c25c628dc061cc21da4bf38cc15c0))

## v0.4.0 (2024-03-04)

### Feature

* Runpip, runuv and runpython subcommands ([`e9b2df1`](https://github.com/robinvandernoord/uvx/commit/e9b2df1d93cdb32fe64bbc04f40f5fc06835c59b))

### Fix

* More dependencies; docs ([`dc0ef76`](https://github.com/robinvandernoord/uvx/commit/dc0ef76c7f0087890841e03bd030aad2d2146e87))

## v0.3.0 (2024-03-04)

### Feature

* Implemented reinstall and list methods, save .metadata file in app-specific venv ([`8a44dab`](https://github.com/robinvandernoord/uvx/commit/8a44dabf39ea91765c87bdabe03e5f30460b954e))

## v0.2.1 (2024-02-29)

### Fix

* Don't crash if currently not in a venv ([`cd480e3`](https://github.com/robinvandernoord/uvx/commit/cd480e3d26e61b864976451c4bc849a4fc2110ea))

## v0.2.0 (2024-02-29)

### Feature

* Implemented basic 'install' and 'uninstall' commands ([`d82261a`](https://github.com/robinvandernoord/uvx/commit/d82261a09b69da94e30614d2e017558c330c80a8))

## v0.1.0 (2024-02-29)

### Feature

* Empty hatch project ([`8358d2a`](https://github.com/robinvandernoord/uvx/commit/8358d2a5b7733cfda4a5c655eec0c15d28221bb2))
