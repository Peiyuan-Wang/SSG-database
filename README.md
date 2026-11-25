# Spin Space Group Database and Enumeration

This repository contains the spin space group enumeration and the offline database for all 230 crystallographic parent space groups. The catalogue has 67,475 entries, including 8,520 continuous families.

- `ssg_enumeration` provides exact enumeration, equivalence tests, naming, and Xiao ID correspondence. See the [Python API](docs/API.md), [algorithm notes](docs/ALGORITHM_NOTES_ZH.md), and [naming convention](docs/label规则.md).
- `ssg_database` provides SQLite import and search, group-operation displays, and the desktop application. See the [user guide](docs/USER_GUIDE.md) and [developer guide](docs/RETRIEVAL_ZH.md).

## Downloads

- [Database v0.9.18](https://github.com/Peiyuan-Wang/SSG-database/releases/tag/v0.9.18) contains the standalone macOS and Windows applications, SQLite catalogue, and Python wheels for that release.
- [Enumeration v0.9.17](https://github.com/Peiyuan-Wang/SSG-database/releases/tag/v0.9.17) contains the standalone enumeration wheel and the exact chart and orbit exports for all 230 parent groups. Those exports are the input for rebuilding SQLite.

## Install from source

Install the checkout in a fresh Python environment. One installation provides both import paths.

```sh
python -m pip install '.[enumeration]'
python example.py
```

The `enumeration` extra adds `spglib` for loading parent groups by their international number. Install `.[desktop]` for the GUI (or `.[desktop-qt5]` for PyQt5) and point it to the SQLite catalogue from the database release.

```sh
python -m pip install '.[desktop]'
python run_desktop.py --database /path/to/SSGclassify.sqlite
```

For tests that use the full database, set `SSG_TEST_DATABASE` to the path to the extracted SQLite file. Run the test suite with `python -m unittest discover -s tests -v`.
