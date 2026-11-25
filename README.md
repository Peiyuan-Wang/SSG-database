# Spin Space Group Database

Browse and search 67,475 spin space group entries from 230 parent space groups, including 8,520 continuous families. The catalogue presents the five-level classification, spin and space operations, continuous-parameter matrix evaluation, and data export. See the [user guide](docs/USER_GUIDE.md).

Download the standalone macOS or Windows application, or the compressed SQLite catalogue, from [Releases](https://github.com/Peiyuan-Wang/SSG-database/releases). The desktop distributions include the full catalogue and the Python code needed for offline use.

## Development

Download the supporting Python wheel from the database release before installing the source checkout.

```sh
python -m pip install /path/to/ssg_enumeration-0.9.17-py3-none-any.whl '.[desktop]'
python run_desktop.py --database /path/to/SSGclassify.sqlite
```

Use `.[desktop-qt5]` to run with PyQt5 or omit the extra for the Python API. Import `SearchDatabase` from `ssg_database`. The standalone builds and the Python API read the same SQLite format.

[Developer guide](docs/RETRIEVAL_ZH.md) covers the catalogue import, tests, and platform builds.
