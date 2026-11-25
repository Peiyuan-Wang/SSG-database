# Spin Space Group Database: retrieval and development

The desktop application uses Qt and a local SQLite database. Its current user documentation is the English [User Guide](USER_GUIDE.md), including the five-level classification, symbols, field-by-field search behavior, worked examples, continuous families, and group-operation displays. This historical filename is retained so existing links continue to work.

## Run from source

```bash
python -m pip install /path/to/ssg_enumeration-0.9.17-py3-none-any.whl '.[desktop]'
python run_desktop.py --database output/retrieval/SSGclassify.sqlite
```

Alternatively, install `.[desktop-qt5]`. Qt is only needed by the desktop interface. The application uses the same database on macOS and Windows and does not require a network connection or TeX at runtime.

## Python

```python
from ssg_database import SearchDatabase
from ssg_enumeration import spin_crystal_class

db = SearchDatabase('output/retrieval/SSGclassify.sqlite')
try:
    result = db.search({'parent': 27, 'bravais': 'oP', 'category': 'P.1.2',
                        'k1': '0,0,1/3', 'q_name': 'C2'})
    print(result['total'])
    for row in result['rows']:
        print(row['xiao'], row.get('matched_specialization'))
    print(db.detail('N143.5.2')['crystal']['kernel'])
    print(db.evaluate('N143.5.2', ['1/7']))
finally:
    db.close()
print(spin_crystal_class('L1.1.1'))
```

`db.children(path)` lists the next classification level. Search `limit` and `offset` control pagination without changing the result count. See `example_retrieval.py` for another example.

## Rebuild and verify

Extract the matching `catalogues` archive from the [SSG Enumeration release](https://github.com/Peiyuan-Wang/SSG-enumeration/releases/tag/v0.9.17). Its parent-group exports are the input to the database build below.

```bash
ssg-build-database \
  --source /path/to/catalogues \
  --output output/retrieval/SSGclassify.sqlite
python scripts/audit_retrieval.py
SSG_TEST_DATABASE=output/retrieval/SSGclassify.sqlite python -m unittest discover -s tests -v
```

When names are changed or a database is rebuilt, generate the vector formulas with LaTeX and dvisvgm available:

```bash
python -m ssg_database.label_svg \
  --database output/retrieval/SSGclassify.sqlite \
  --workdir tmp/latex_labels --workers 4
```

The build retains TeX/DVI/SVG intermediates, formula verification, source hashes and database audit reports. `scripts/build_desktop.py` builds the macOS application; `scripts/build_windows.py` builds on Windows. The [User Guide](USER_GUIDE.md) states the limitations of continuous-family profiles and joint searches.

Install PyInstaller in the same environment before building a standalone application. The macOS script uses PyQt5 and the Windows script uses PySide6. Supply the SQLite file as `--database`. The Windows GitHub workflow takes a release tag and reads the SQLite archive and pinned core wheel from that release before building and testing the executable.
