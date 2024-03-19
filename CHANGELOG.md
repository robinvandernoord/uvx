# Changelog

<!--next-version-placeholder-->

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
