"""Launch and package the Windows executable, with no source/Python path dependencies."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DATABASE_SHA256 = '075a65d8b1e4bbde3ce535e308d78ddbbc58528bcd5efd661cec1242011a8b56'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def main():
    if sys.platform != 'win32':
        raise SystemExit('This verification must run on Windows.')
    version = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    source = ROOT / 'output/retrieval/windows/Spin Space Group Database'
    # Exercise spaces, Unicode and URI-reserved characters in the installed path.
    destination = ROOT / 'tmp/Windows 验证 #1/Spin Space Group Database'
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), destination)
    database = destination / '_internal/SSGclassify.sqlite'
    if digest(database) != DATABASE_SHA256:
        raise RuntimeError('Bundled database differs from the released database.')
    output = ROOT / 'dist/windows'
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / 'windows-validation.json'
    preview = output / 'windows-preview.png'
    env = {key: value for key, value in os.environ.items()
           if key not in {'PYTHONPATH', 'PYTHONHOME', 'QT_QPA_PLATFORM', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH'}}
    executable = destination / 'Spin Space Group Database.exe'
    # GUI applications have no console. Wait on the actual process and read its structured report.
    result = subprocess.run([str(executable), '--smoke-test', '--smoke-report', str(report_path),
                             '--smoke-screenshot', str(preview)], cwd=destination.parent,
                            env=env, timeout=120)
    if result.returncode:
        raise RuntimeError(f'Frozen GUI exited with code {result.returncode}')
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if not report['ok'] or not report['frozen'] or not preview.is_file():
        raise RuntimeError('Frozen GUI verification did not complete.')
    if Path(report['database']).resolve() != database.resolve():
        raise RuntimeError('Executable did not use its bundled database.')
    if digest(database) != DATABASE_SHA256:
        raise RuntimeError('Read-only queries changed the database.')
    missing_report = output / 'windows-missing-database.json'
    missing = subprocess.run([str(executable), '--database', str(destination / 'missing.sqlite'),
                              '--smoke-test', '--smoke-report', str(missing_report)],
                             cwd=destination.parent, env=env, timeout=60)
    if missing.returncode != 1 or json.loads(missing_report.read_text(encoding='utf-8'))['ok']:
        raise RuntimeError('Missing database did not fail cleanly.')
    report.update(database_sha256=DATABASE_SHA256,unicode_install_path=True,
                  missing_database_exit_code=missing.returncode,
                  source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutil.copy2(report_path,destination / 'windows-validation.json')
    archive = output / f'Spin-Space-Group-Database-v{version}-windows-x64.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(destination.rglob('*')):
            if path.is_file():
                z.write(path,Path('Spin Space Group Database') / path.relative_to(destination))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise RuntimeError('ZIP integrity check failed.')
    (output / 'SHA256SUMS-windows.txt').write_text(
        ''.join(f'{digest(path)}  {path.name}\n' for path in
                [archive,report_path,preview,missing_report]),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))
    print(archive)


if __name__ == '__main__':
    main()
