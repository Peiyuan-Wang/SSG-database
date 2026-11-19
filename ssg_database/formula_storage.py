"""Lossless, bounded-block storage for precompiled vector formulae."""
import hashlib
import os
from pathlib import Path
import sqlite3
import struct
import tempfile
import zlib


def decode_formula_block(blob):
    """Decode a length-prefixed block into the original SVG byte strings."""
    try:raw=zlib.decompress(blob)
    except zlib.error as exc:raise ValueError('Corrupt formula block') from exc
    offset=0;result=[]
    while offset<len(raw):
        if offset+4>len(raw):raise ValueError('Truncated formula block')
        length=struct.unpack_from('>I',raw,offset)[0];offset+=4
        if length==0 or offset+length>len(raw):raise ValueError('Invalid formula length')
        result.append(raw[offset:offset+length]);offset+=length
    if not result:raise ValueError('Empty formula block')
    return tuple(result)


def compact_formula_database(source,destination,*,block_size=64):
    """Create a compact copy; leave the source and existing files untouched.

    SVGs remain exactly the same bytes. Each block belongs to one parent group
    and contains at most ``block_size`` length-prefixed formulae.
    """
    source=Path(source).resolve();destination=Path(destination).resolve()
    if source==destination:raise ValueError('Source and destination must differ')
    if not source.is_file():raise FileNotFoundError(source)
    if destination.exists():raise FileExistsError(destination)
    if type(block_size) is not int or not 1<=block_size<=1024:raise ValueError('Invalid block size')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.formula-compact-',dir=destination.parent) as scratch:
        copy=Path(scratch)/'work.sqlite';staged=Path(scratch)/'compact.sqlite'
        src=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)
        dst=sqlite3.connect(copy)
        try:
            columns={row[1] for row in src.execute('PRAGMA table_info(label_formulas)')}
            if not {'class_id','latex_sha256','svg'}<=columns:raise ValueError('Expected the original per-formula SVG format')
            classes=src.execute('SELECT count(*) FROM classes').fetchone()[0]
            labels=src.execute('SELECT count(*) FROM label_formulas').fetchone()[0]
            if labels!=classes or src.execute('SELECT 1 FROM classes c LEFT JOIN label_formulas f ON f.class_id=c.id WHERE f.class_id IS NULL LIMIT 1').fetchone():
                raise ValueError('Formula catalogue does not match classes')
            src.backup(dst)
            dst.execute('CREATE TABLE label_formula_blocks(id INTEGER PRIMARY KEY,parent INTEGER NOT NULL,data BLOB NOT NULL)')
            dst.execute('CREATE TABLE label_formulas_compact(class_id TEXT PRIMARY KEY,latex_sha256 TEXT NOT NULL,block_id INTEGER NOT NULL,position INTEGER NOT NULL)')
            parent=None;vectors=[];entries=[];blocks=0;count=0
            def flush():
                nonlocal blocks
                blocks+=1
                raw=b''.join(struct.pack('>I',len(svg))+svg for svg in vectors)
                dst.execute('INSERT INTO label_formula_blocks VALUES(?,?,?)',(blocks,parent,zlib.compress(raw,6)))
                dst.executemany('INSERT INTO label_formulas_compact VALUES(?,?,?,?)',
                                ((cid,sha,blocks,i) for i,(cid,sha) in enumerate(entries)))
            query='SELECT c.parent,c.id,c.liu_latex,f.latex_sha256,f.svg FROM classes c JOIN label_formulas f ON f.class_id=c.id ORDER BY c.parent,c.id'
            for p,cid,latex,sha,blob in src.execute(query):
                if vectors and (p!=parent or len(vectors)>=block_size):
                    flush();vectors=[];entries=[]
                parent=p
                if hashlib.sha256(latex.encode()).hexdigest()!=sha:raise ValueError('Formula hash mismatch: '+cid)
                try:svg=zlib.decompress(blob)
                except zlib.error as exc:raise ValueError('Corrupt SVG: '+cid) from exc
                if not svg or b'<path' not in svg or b'<image' in svg:raise ValueError('Invalid vector formula: '+cid)
                vectors.append(svg);entries.append((cid,sha));count+=1
            if vectors:flush()
            if count!=classes:raise ValueError('Incomplete formula conversion')
            dst.execute('DROP TABLE label_formulas')
            dst.execute('ALTER TABLE label_formulas_compact RENAME TO label_formulas')
            dst.commit()
            dst.execute('VACUUM INTO ?', (str(staged),))
            dst.close();dst=None
            check=sqlite3.connect(staged.as_uri()+'?mode=ro',uri=True)
            try:
                if check.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Compact database integrity check failed')
            finally:check.close()
            # The hard link is atomic and fails if a destination appeared while building.
            os.link(staged,destination)
            return {'formulas':count,'blocks':blocks,'block_size':block_size,
                    'source_bytes':source.stat().st_size,'destination_bytes':destination.stat().st_size}
        finally:
            if dst is not None:dst.close()
            src.close()
