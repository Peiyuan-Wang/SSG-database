"""Reproducible macOS .app build; invoke with an environment containing Qt."""
from pathlib import Path
import argparse
import os
import plistlib
import subprocess
import sys
import tomllib

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--database',type=Path,default=ROOT/'output/retrieval/SSGclassify.sqlite')
parser.add_argument('--output',type=Path,default=ROOT/'output/retrieval/app')
parser.add_argument('--app-name',default='SSGclassify')
parser.add_argument('--bundle-id',default='org.ssgclassify.desktop')
args=parser.parse_args()
db=args.database.resolve();output=args.output.resolve()
if not db.is_file():raise SystemExit('Build the complete database first.')
if db.name!='SSGclassify.sqlite':raise SystemExit('The bundled database must be named SSGclassify.sqlite.')
command=[sys.executable,'-m','PyInstaller','--noconfirm','--windowed','--onedir',
         '--name',args.app_name,'--osx-bundle-identifier',args.bundle_id,
         '--distpath',str(output),
         '--workpath',str(ROOT/'tmp/desktop-build'),
         '--specpath',str(ROOT/'tmp'),
         '--add-data',str(db)+':.',
         '--add-data',str(ROOT/'ssg_database/data')+':ssg_database/data',
         '--collect-data','ssg_enumeration',
         '--exclude-module','PySide6','--exclude-module','tkinter',
         '--exclude-module','IPython','--exclude-module','notebook',
         '--exclude-module','pandas','--exclude-module','scipy',
         '--exclude-module','matplotlib','--exclude-module','numpy',
         '--exclude-module','PIL','--exclude-module','lxml',
         '--exclude-module','pytest','--exclude-module','sympy.testing',
         str(ROOT/'run_desktop.py')]
environment=dict(os.environ)
environment['PYINSTALLER_CONFIG_DIR']=str(ROOT/'tmp/pyinstaller-cache')
environment['MPLBACKEND']='Agg'
subprocess.run(command,cwd=ROOT,env=environment,check=True)
app=output/(args.app_name+'.app')
plist=app/'Contents/Info.plist'
version=tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
metadata=plistlib.loads(plist.read_bytes());metadata['CFBundleShortVersionString']=version;metadata['CFBundleVersion']=version
plist.write_bytes(plistlib.dumps(metadata))
subprocess.run(['codesign','--force','--deep','--sign','-',str(app)],check=True)
print(app)
