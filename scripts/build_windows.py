"""Build the offline x64 Windows application on a native Windows host."""
import argparse
from importlib import metadata
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=ROOT / 'output/retrieval/SSGclassify.sqlite')
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Run this build on Windows; the macOS build cannot generate a Windows executable.')
    if sys.maxsize <= 2**32:
        parser.error('Use 64-bit Python.')
    database = args.database.resolve()
    if not database.is_file():
        parser.error(f'Missing database: {database}')
    version = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    output = ROOT / 'output/retrieval/windows'
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
               '--windowed', '--onedir', '--name', 'Spin Space Group Database',
               '--distpath', str(output), '--workpath', str(ROOT / 'tmp/windows-build'),
               '--specpath', str(ROOT / 'tmp'),
               '--add-data', f'{database}{os.pathsep}.',
               '--add-data', f'{ROOT / "ssg_database/data"}{os.pathsep}ssg_database/data']
    command += ['--collect-data', 'ssg_enumeration']
    for name in ['PyQt5', 'PyQt6', 'PySide2', 'tkinter', 'IPython', 'notebook',
                 'pandas', 'scipy', 'matplotlib', 'numpy', 'PIL', 'lxml', 'pytest', 'sympy.testing']:
        command += ['--exclude-module', name]
    command += [str(ROOT / 'run_desktop.py')]
    env = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(ROOT / 'tmp/pyinstaller-windows-cache'))
    subprocess.run(command, cwd=ROOT, env=env, check=True)
    bundle = output / 'Spin Space Group Database'
    shutil.copy2(ROOT / 'docs/USER_GUIDE.md', bundle / 'USER_GUIDE.md')
    # Include the installed distributions' license texts without bundling their build tools.
    notices = bundle / 'third-party-licenses'
    for package in ['PySide6-Essentials', 'shiboken6', 'sympy', 'mpmath']:
        distribution = metadata.distribution(package)
        for entry in distribution.files or []:
            if not any('license' in part.lower() or part.lower().startswith('copying') for part in entry.parts):
                continue
            source = Path(distribution.locate_file(entry))
            if source.is_file():
                target = notices / package / str(entry).replace('..', '_')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    (bundle / 'VERSION.txt').write_text(version + '\n', encoding='utf-8')
    print(bundle / 'Spin Space Group Database.exe')


if __name__ == '__main__':
    main()
