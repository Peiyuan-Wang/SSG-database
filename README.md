# SSG Enumeration

This repository contains the exact enumeration and classification of spin space groups for the 230 parent space groups. The Python package covers representations, spin and spatial equivalences, continuous families, naming, Xiao ID correspondence, and the spin images \(H\), \(K\), and \(Q\).

Install the core with `python -m pip install .`. Use `python -m pip install '.[database]'` to add spglib for loading parent groups by their international number. Run `python example.py` or read the [Python API](docs/API.md). Verification is available through `python -m unittest discover -s tests -v`. The [algorithm explanation](docs/ALGORITHM_NOTES_ZH.md) and [naming convention](docs/label规则.md) are in this repository.

The [Spin Space Group Database](https://github.com/Peiyuan-Wang/SSG-database) is the companion application. It consumes this package and the exported parent-group catalogues. The core wheel and the catalogue archive are available in [Releases](https://github.com/Peiyuan-Wang/SSG-enumeration/releases). For database builds, extract the archive to obtain the files `001.json.gz` through `230.json.gz`. These files contain the exact charts and orbit lists used to match the bundled naming catalogue.

The previous combined project is [SSGclassify](https://github.com/Peiyuan-Wang/SSGclassify). This repository was split from commit `33367de7652fae807f866a85ad495aae92989bb3`.
