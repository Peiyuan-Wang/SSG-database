# Spin Space Group Database for Windows

This historical filename is retained for existing links. The current English [User Guide](USER_GUIDE.md) explains the classification, search fields and group operations.

## Launch

Extract the entire Windows x64 archive, open the `Spin Space Group Database` folder, and run `Spin Space Group Database.exe`. Keep the `_internal` folder alongside the executable. Python, Qt, TeX, administrator access and a network connection are not required at runtime. The target is 64-bit Windows 10 (1809 or later) or Windows 11 on Intel/AMD hardware.

macOS and Windows use the same SQLite database. The currently supplied database has SHA-256:

```
c35a7a2826ea62ce10d4ec06940341c45ebaf87f75a68d398a5688c9faf2b452
```

## Use an external database

```powershell
& ".\Spin Space Group Database.exe" --database "D:\SSG data\SSGclassify.sqlite"
```

## Build on Windows

```powershell
python -m pip install ".[database]" "PySide6-Essentials==6.8.3" "pyinstaller==6.16.0"
python scripts/build_windows.py --database "D:\SSG data\SSGclassify.sqlite"
python scripts/verify_windows.py
```

The Windows build is produced and tested on a Windows host; see the workflow for the actual environment and checks. Windows 10/11 are compatibility targets, not a claim of manual testing on every version.
