"""Read the compiled PDF, not just its TeX input, to check every published ID."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'tmp/pdfs/label_table'
manifest=json.loads((WORK/'manifest.json').read_text())
expected=manifest['xiao_ids']
actual=re.findall(r'\b[LPN]\d+\.\d+\.\d+\b',(WORK/'compiled.txt').read_text())
assert actual==expected, (len(actual),len(expected),list((Counter(actual)-Counter(expected)).items())[:5],list((Counter(expected)-Counter(actual)).items())[:5])
compiled_rows=(WORK/'SSG_labels_Xiao_67475.rows').read_text().splitlines()
assert compiled_rows==expected
reader=PdfReader(WORK/'SSG_labels_Xiao_67475.pdf')
outline=reader.outline
assert len(outline)==231
destinations={item.title:reader.get_destination_page_number(item)+1 for item in outline}
assert sum(title.startswith('SG ') for title in destinations)==230
pages=(WORK/'compiled.txt').read_text().split('\f')
source=json.loads(gzip.decompress((ROOT/'ssg_enumeration/data/ssg_names.json.gz').read_bytes()))
longest=max(source['rows'],key=lambda r:len(r['latex']))
longest_page=next(i+1 for i,page in enumerate(pages) if re.search(r'\b'+re.escape(longest['xiao'])+r'\b',page))
samples={1,2,3,len(reader.pages),longest_page}
for number in (4,47,143,146,224):
    samples.add(next(page for title,page in destinations.items() if title.startswith(f'SG {number}:')))
report={'rows':len(actual),'unique_xiao_ids':len(set(actual)),'parent_bookmarks':230,
        'pages':len(reader.pages),'pdf_readback_matches_source_order':True,
        'tex_emitted_rows_match_source':True,'exact_matrix_symbol_replacements':len(manifest['exact_matrix_symbol_replacements']),
        'shared_parameter_domain_families':manifest.get('shared_parameter_domain_families'),
        'continuous_parameter_counts':manifest.get('parameter_counts'),
        'longest_formula':{'id':longest['id'],'xiao':longest['xiao'],'page':longest_page},
        'visual_sample_pages':sorted(samples),
        'pdf_sha256':hashlib.sha256((WORK/'SSG_labels_Xiao_67475.pdf').read_bytes()).hexdigest(),
        'tex_sha256':manifest['tex_sha256']}
(WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
