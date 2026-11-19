"""Render the complete formal-label/Xiao correspondence as standalone XeLaTeX."""
from collections import Counter
from functools import lru_cache
import gzip
import hashlib
import json
import re
from math import gcd
from pathlib import Path

from sympy import ImmutableMatrix as M, latex, simplify
from ssg_enumeration.naming import _spin_matrix, _spin_latex, _expr, _settings

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/pdf'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT / 'ssg_enumeration/data/ssg_names.json.gz'


@lru_cache(maxsize=None)
def compact_matrix_symbol(token):
    """Replace a matrix superscript only after exact Rodrigues reconstruction."""
    m = _spin_matrix(token)
    sign = int(m.det())
    r = sign*m
    axis = (r-M.eye(3)).nullspace()[0]
    axis = axis/next(x for x in axis if x != 0)
    if axis == M([1,0,0]): axis_token='x'
    elif axis == M([0,1,0]): axis_token='y'
    elif axis == M([0,0,1]): axis_token='z'
    else: axis_token='['+','.join(str(simplify(x)) for x in axis)+']'
    for n in (2,3,4,6,8,12,16,24,48):
        for power in range(1,n):
            if gcd(n,power) != 1: continue
            proposed=('-' if sign==-1 else '')+f'{n}_{axis_token}^{power}'
            try: recovered=_spin_matrix(proposed)
            except ValueError: continue
            if recovered == m:
                a=axis_token
                if a.startswith('['): a='['+','.join(latex(_expr(x)) for x in a[1:-1].split(','))+']'
                return _spin_latex(m),('-' if sign==-1 else '')+str(n)+'_{'+a+'}^{'+str(power)+'}'
    raise ValueError(('No exact compact rotation symbol',token))


def build():
    data=json.loads(gzip.decompress(SOURCE.read_bytes()))
    rows=data['rows']
    assert len(rows)==67475 and len({r['text'] for r in rows})==67475
    assert len({r['xiao'] for r in rows})==67475
    families=[r for r in rows if r['name']['basis'][0]]
    assert len(families)==8520 and all(r['name']['general'] for r in families)
    for row in families:
        d=len(row['name']['basis'][0])
        expected=','.join('u_{'+str(j)+'}' for j in range(d))+r'\in\mathbb R/\mathbb Z,\quad 2C_B^T\mathbf k\notin\mathbb Z^3'
        assert row['latex'].split(r',\quad ',1)[1]==expected
    replacements={}
    for row in rows:
        for token in row['name']['spins']:
            if token.startswith('M['):
                old,new=compact_matrix_symbol(token)
                replacements[old]=new
    header=r'''% !TeX program = xelatex
% Self-contained full correspondence: 67,475 classes, 230 parent space groups.
% Compile twice: xelatex -interaction=nonstopmode -halt-on-error SSG_labels_Xiao_67475.tex
\documentclass[a4paper,10pt]{article}
\usepackage[margin=17mm,top=19mm,bottom=19mm,headheight=14pt,headsep=5mm,footskip=9mm]{geometry}
\usepackage{fontspec,xeCJK}
\setmainfont[BoldFont=texgyretermes-bold.otf,ItalicFont=texgyretermes-italic.otf,BoldItalicFont=texgyretermes-bolditalic.otf]{texgyretermes-regular.otf}
\setsansfont[BoldFont=texgyreheros-bold.otf]{texgyreheros-regular.otf}
\setCJKmainfont[BoldFont=FandolSong-Bold.otf]{FandolSong-Regular.otf}
\setCJKmonofont{FandolSong-Regular.otf}
\usepackage{amsmath,amssymb,array,longtable,booktabs,fancyhdr}
\usepackage[unicode,hidelinks,bookmarksnumbered=false]{hyperref}
\usepackage{bookmark}
\hypersetup{pdftitle={SSG 正式名称与 Xiao 完整编号对应表},pdfauthor={SSGclassify},pdfsubject={67,475 classes; naming convention v1.1}}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5pt}
\setlength{\LTpre}{6pt}
\setlength{\LTpost}{0pt}
\setlength{\LTleft}{0pt}
\setlength{\LTright}{0pt}
\setlength{\tabcolsep}{5pt}
\setcounter{LTchunksize}{80}
\renewcommand{\arraystretch}{1.12}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small SSG 正式名称与 Xiao 编号}
\fancyhead[R]{\small\nouppercase{\leftmark}}
\fancyfoot[C]{\small\thepage}
\renewcommand{\headrulewidth}{0.3pt}
\newwrite\rowaudit
\immediate\openout\rowaudit=SSG_labels_Xiao_67475.rows
\newcounter{cataloguerows}
\newcommand{\entry}[2]{\stepcounter{cataloguerows}\immediate\write\rowaudit{#2}\rule[-3pt]{0pt}{15pt}$#1$&\rule[-3pt]{0pt}{15pt}\(\mathrm{#2}\)\\}
\begin{document}
\pdfbookmark[0]{说明}{intro}
{\LARGE\bfseries SSG 正式名称与 Xiao 编号对应表}\par
{\large 230 个母空间群\quad 67,475 个分类}\par
\vspace{3mm}
本表采用 SSGclassify v0.4.0 的命名规则 v1.1，逐项列出正式名称及 Xiao 等论文目录中的完整编号。
共线、共面、非共面分类分别为 1,421、9,542、56,512，其中连续族为 8,520 个。

\textbf{读法。} 按 Liu 等的记号在名称末尾标出自旋专属群：
共线为 $^{\infty m}\!1$，共面为 $^{m}\!1$；非共面的自旋专属群为恒等群，末尾省略。
空间群符号上的上标为自旋操作。原程序中的 L/P/N 前缀与上述末尾标记一一对应。
轴向平移用惯用胞倒格坐标 $\mathbf k$ 表示，点操作上标已按命名约定扣除分数平移相位。
尖括号依次给出三个固定 HNF 原胞平移的真转动像。
共面分支使用 $\operatorname{diag}(D,\det D)$ 的保向三维提升。

\textbf{连续参数的统一约定（适用于所有含 $u_j$ 的名称）。}
若一行出现 $u_0,\ldots,u_{d-1}$，其完整参数域统一为
\[
\boxed{\displaystyle
\mathcal U=\left\{\mathbf u\in(\mathbb R/\mathbb Z)^d:
2C_B^T\mathbf k(\mathbf u)\notin\mathbb Z^3\right\}.}
\]
各参数均以 1 为周期，可取 $0\leq u_j<1$。
设惯用胞基为 $A$，固定 HNF 原胞基为 $A_{\rm p}=A C_B$，则
$\mathbf q=C_B^T\mathbf k$ 是同一波矢的原胞倒格坐标。
上式中的 $2C_B^T\mathbf k=2\mathbf q$，因此排除的是
\textbf{$2q_1,2q_2,2q_3$ 同时为整数}的点，即 TRIM（包含零波矢）。
这些特殊表示在其所属类型中另列；并非要求三个分量各自都不是整数。

\textbf{统一判据不等于相同的被排除参数值。}
$C_B$ 依母群而定，$\mathbf k(\mathbf u)$ 依本行公式而定。
例如在 $C_B=I$ 时，$\mathbf k=(0,0,u)$ 对应 $2u\notin\mathbb Z$，
而 $P2_1$ 螺旋族的 $\mathbf k=(0,2u,0)$ 对应 $4u\notin\mathbb Z$。
本表的 8,520 个连续族均采用上述统一约定，故不在每行重复打印参数域。
本约定\textbf{不适用于不含连续参数的离散条目}。
公式保留螺旋分支的覆盖次数，不对波矢逐点折回基本域。

\textbf{操作与设定。} 每个母群采用程序固定的 Hall 设定，表头给出 Hall 编号。
复合 HM 位置的分子和分母分别带上标。自旋符号 $n_{\hat a}^{j}$ 表示绕有向轴 $\hat a$
旋转 $2\pi j/n$；$m_{\hat a}$ 的下标为法向。少数较长的矩阵上标在本表中以精确相同的轴角符号排版，未改变其自旋操作。

\textbf{检验。} 67,475 个名称逐项通过解析、恢复表示与重新命名；对应关系和既有分类数量保持一致。
此为命名层面的回算验证，不增加关于历史 Xiao 表示匹配的证明声明。
可用 PDF 书签定位母空间群，也可搜索完整 Xiao 编号。

\textbf{参考。} Xiao 等，\textit{Physical Review X} \textbf{14}, 031037 (2024)；
Chen 等，\textit{Physical Review X} \textbf{14}, 031038 (2024)，补充材料 Tables S3--S9。
具体命名约定和标准操作见项目文档 \texttt{docs/LABEL\_USAGE\_ZH.md}。
'''
    out=[header]
    settings=_settings()
    groups={n:[] for n in range(1,231)}
    for row in rows: groups[row['name']['space_group']].append(row)
    counts=[]
    for number, group in groups.items():
        # Preserve the established correspondence ordering within each parent.
        setting=settings[str(number)]
        hm=re.sub(r'-([1346])',lambda m:r'\overline{'+m[1]+'}',setting['hm']).replace(' ','\\,')
        bookmark_hm=setting['hm'].replace('_','')
        out.append(r'\clearpage'+ '\n'+rf'\pdfbookmark[0]{{SG {number}: {bookmark_hm}}}{{sg{number}}}'+ '\n')
        out.append(rf'\markboth{{SG {number}\quad Hall {setting["hall_number"]}}}{{}}'+'\n')
        out.append(rf'{{\large\bfseries 母空间群 {number}\quad \( {hm} \)}}\par'+'\n')
        out.append(rf'Hall 编号 {setting["hall_number"]}\quad 本组 {len(group):,} 个分类\quad 连续族 {sum(bool(r["name"]["basis"][0]) for r in group):,} 个'+'\n')
        out.append(r'''\fontsize{10}{13}\selectfont
\begin{longtable}{@{}>{\raggedright\arraybackslash}p{142mm}>{\raggedright\arraybackslash}p{30mm}@{}}
\toprule
\textbf{新 label（正式名称）} & \textbf{Xiao 完整编号}\\
\midrule
\endfirsthead
\toprule
\textbf{新 label（正式名称）} & \textbf{Xiao 完整编号}\\
\midrule
\endhead
\bottomrule
\endfoot
''')
        for row in group:
            formula=row['latex']
            for old,new in replacements.items(): formula=formula.replace(old,new)
            if r'\begin{matrix}' in formula: raise ValueError(('Uncompacted matrix',row['id']))
            parts=formula.split(r',\quad ',1)
            main=re.sub(r'-([1346])(?=\\,|/|$)',lambda m:r'\overline{'+m[1]+'}',parts[0])
            dim=row['name']['dimension']
            prefix=r'\mathrm{'+dim+r'}:\;'
            assert main.startswith(prefix)
            main=main[len(prefix):]
            main += {'L':r'\,{}^{\infty m}\!1','P':r'\,{}^{m}\!1','N':''}[dim]
            main=main.replace(r'\,',r'\,\allowbreak ')
            out.append(f'% {row["id"]}\n'+r'\entry{'+main+'}{'+row['xiao']+'}\n')
        out.append('\\end{longtable}\n')
        counts.append({'space_group':number,'rows':len(group)})
    out.append(r'\typeout{CATALOGUE-ROWS=\arabic{cataloguerows}}'+'\n'+r'\immediate\closeout\rowaudit'+'\n'+r'\end{document}'+'\n')
    target=OUT/'SSG_labels_Xiao_67475.tex'
    target.write_text(''.join(out))
    manifest={'rows':len(rows),'parents':len(groups),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              'tex_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'exact_matrix_symbol_replacements':replacements,
              'group_counts':counts,'shared_parameter_domain_families':len(families),
              'parameter_counts':dict(Counter(len(r['name']['basis'][0]) for r in families)),
              'xiao_ids':[r['xiao'] for group in groups.values() for r in group]}
    (ROOT/'tmp/pdfs/label_table/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print('Wrote',target,len(rows),'rows;',len(replacements),'exact matrix/axis-angle replacements')


if __name__=='__main__': build()
