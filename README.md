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

To compare two offline copies of a slot directory, run `gta6-save compare-slots SLOT_A SLOT_B`. Each JSON line identifies an added, removed or modified file by relative path, with sizes and SHA-256 hashes. Identical directories produce no output. Renames appear as a removal and an addition. Links inside the directories are skipped.

For VIctory captures, use `gta6-save victory-manifest PATH/TO/manifest` to identify corresponding blobs across versions. See the [collection procedure](docs/COLLECTION.md#collecting-from-victory).

## Find a candidate integer field

Run `python examples/find_balance.py` from the repository root for a self-checking synthetic example. With private offline copies of the same logical blob and values observed in game, use:

```console
gta6-save find-integer --sample A 2000 --sample A2 2000 --sample B 1750 --sample C 1500 --predict D
```

Each JSON line gives a matching byte offset and the prediction from D. Check it against an independently recorded observation. The search assumes a fixed offset and an unsigned, uncompressed integer. Set `--width` to 1, 2, 4 or 8 bytes (default 4) and `--byteorder` to little or big (default little). Multiple matches remain candidates. No matches produce empty output. A prediction of null means the held-out file ends before the field is complete.

## Test an edit on an offline copy

Run `python examples/find_balance.py` for a synthetic example that finds an
offset, predicts the value in a held-out file, and changes that value in a
separate verified copy. For an independently verified field, take the input
digest from `gta6-save inspect`, then pass it to the patch command:

```console
gta6-save patch-integer D D-edited --sha256 INPUT_DIGEST --offset 12 --width 4 --byteorder little --expect 1475 --value 1600
```

The command requires the exact input SHA-256 and the expected old value. It
verifies the output before publishing it at a new path. The destination
filesystem must support hard links, as NTFS does. The command works on raw
unsigned integers at fixed offsets. GTA VI field layouts and save integrity
checks still require validation with real saves.

## Track save support

Use `gta6-save capture SNAPSHOT --commit COMMIT` for a local JSON report on an
offline VIctory save directory. Add `--previous EARLIER_SNAPSHOT` to compare
the logical blobs across copies. See the [capture instructions](docs/COLLECTION.md#collecting-from-victory).

Every six hours, [Port save watch](../../actions/workflows/watch.yml) checks recent GitHub issues, pull requests and releases from the projects in [the watch list](scripts/ports.json). It scans titles and descriptions updated within the last 14 days, grouping new matching URLs into one triage issue per project per scan. Previous bot issues, including closed ones, record links already reported. Reports may describe failures. Follow the [collection protocol](docs/COLLECTION.md) to verify a build.

Run `python scripts/watch_ports.py` with an authenticated GitHub CLI to preview matches locally. Maintainers can also trigger the workflow from the Actions tab.

## Contribute

Pull requests and reproducible observations are welcome. See the [contribution guide](CONTRIBUTING.md), [roadmap](ROADMAP.md) and [MIT license](LICENSE). This is an independent community project.
