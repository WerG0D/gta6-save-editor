# Roadmap

| Milestone | Acceptance criteria |
| --- | --- |
| Research CLI | Contributors can install on Windows, inspect files and reproduce a positional diff using synthetic data. |
| First local slot | A named build saves a story-mode slot and reloads its progress after a restart. Record control snapshots and hashes using the collection protocol. |
| First decoded field | Predict a visible value on a held-out slot before checking it in game. An unmodified serialization reproduces the original bytes. |
| First edit | Validate field bounds and format, preserve unknown regions and write a separate copy. Another tester loads the changed value, continues playing, saves and reloads it on the same build. |
| Public editor release | Publish the Windows package, checksums, restoration instructions and a compatibility matrix by build and operation. |

Keep the parser independent of the CLI so a future graphical interface can reuse it. Block writes for unknown formats, truncated inputs and unsupported integrity checks. Keep original slots intact on write failures. Use redistributable synthetic fixtures in CI.
