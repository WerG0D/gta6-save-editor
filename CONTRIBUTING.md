# Contributing

Open an issue to share a hypothesis, reproducible failure or build observation. Code, documentation, synthetic fixtures and public watch-list sources are welcome.

Fork the repository, create a branch and run `python -m unittest discover -s tests -v`. Open a pull request against `main` with expected behavior and reproduction steps. Link the collection issue and include a synthetic test for any newly decoded field. CI checks Windows and Linux.

To suggest a port, edit `scripts/ports.json` and explain its relevance to GTA VI in the pull request. Set `require_game_name` to true for compatibility layers that support several games. Write repository content in English. Contributions are distributed under the MIT license.
