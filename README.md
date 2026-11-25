# GTA VI Save Editor

Open-source research tools for local GTA VI story-mode saves. The CLI reads and compares binary files. Support for editing a real save depends on reproducing a save-and-reload cycle on an identified PC build.

## Try the CLI

From the repository root with Python 3.11 or later:

```console
python -m pip install .
gta6-save inspect README.md
gta6-save diff README.md README.md
```

Replace the example paths with copies of your files. `inspect` prints the filename, size in bytes and SHA-256 digest as JSON. `diff` prints one JSON object per changed byte range, using decimal offsets with an inclusive start and exclusive end. Equal files produce no output. Successful comparisons exit with status 0 even when files differ. Read errors return 1. To run directly from source, use `python gta6_save.py` in place of `gta6-save`.

## Track save support

Every six hours, [Port save watch](../../actions/workflows/watch.yml) checks recent GitHub issues, pull requests and releases from the projects in [the watch list](scripts/ports.json). It scans titles and descriptions updated within the last 14 days, grouping new matching URLs into one triage issue per project per scan. Previous bot issues, including closed ones, record links already reported. Reports may describe failures. Follow the [collection protocol](docs/COLLECTION.md) to verify a build.

Run `python scripts/watch_ports.py` with an authenticated GitHub CLI to preview matches locally. Maintainers can also trigger the workflow from the Actions tab.

## Contribute

Pull requests and reproducible observations are welcome. See the [contribution guide](CONTRIBUTING.md), [roadmap](ROADMAP.md) and [MIT license](LICENSE). This is an independent community project.
