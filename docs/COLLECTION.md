# Collect a reproducible save sample

1. Record the port URL, exact commit or release, game version, operating system and compatibility layer. Use story mode, a dedicated test slot and a recoverable copy of your personal files.
2. Save slot A. Close the game before copying the entire slot directory to private storage. Record the UTC time, visible progress, character and value under study. Inventory relative filenames and run `gta6-save inspect FILE` for sizes and SHA-256 hashes.
3. Restart the same build and reload A. Record which values and progress return. When available, disable cloud synchronization in the test profile and repeat to establish local persistence. Document uncertainty about the data source.
4. Save A2 with the same observable state. Change one known value, for example by purchasing an item, and save B. Repeat with a different value for C. Close the game before taking each snapshot. Note side effects such as time, inventory and character changes.
5. Compare the directory inventories. Record added, deleted and renamed files. Run `gta6-save diff BEFORE AFTER` on corresponding files for A/A2, A/B and B/C. Inserting bytes can shift all later offsets.
6. Reserve a separate slot for validating predictions. Open a collection issue with sanitized relative paths, observations and reproduction steps. Keep personal saves, account identifiers, executables and game assets out of public reports.

A maintainer reproduces the save and reload on the identified build, records the files involved and opens a parser task for the first independently verifiable field.
