# 正式名称与程序使用（v0.4.0）

本版实现 [label 规则 v1.1](label规则.md)。正式名称使用 L/P/N 前缀、完整 Hermann–Mauguin 符号、惯用胞波矢与自旋上标；连续族的参数域属于名称的一部分。原有 17 类类型、短编号和 Xiao 完整编号分别保留，不改变分类等价关系和分类数量。

## 1. 安装与最小调用

```bash
python -m pip install .
python example_labels.py
```

```python
from sympy import Rational
from ssg_enumeration import name_for_label, parse_label, to_xiao_label

name = name_for_label("N143.5.2")   # 也接受 SG143/N.1.2/0002
print(name.text)                  # 可解析的正式名称
print(name.latex)                 # 排版用 LaTeX，不含外层美元符号
print(name.liu_latex)             # 用 Liu 风格后缀代替 L:/P:/N:，不含外层美元符号
print(name.parameter_domain)
print(to_xiao_label(name.text))    # N143.5.2

restored = parse_label(name.text)  # 默认检查群关系
u = [Rational(1, 11)] * restored.parameter_count
matrix = restored.evaluate((0, 0, 0), point=1, parameters=u)
record = restored.to_record()     # 恢复包内可计算的 SSG 对象
print(record.category)            # 17 类类型
print(record.name(143).text)      # 回到同一规范名称
```

`evaluate` 的平移是三个固定 HNF 原胞基矢的整数系数，`point` 是固定截面下标；二者不是惯用胞的分数坐标。`parameters` 使用精确有理数。输入排除的 TRIM/零波矢成员会抛出异常，应查询它所属的独立分类。

`name.evaluate` 在名称规定的自旋坐标架中输出矩阵。`name.to_record()` 将轴向反轴相位恢复到枚举器的 `theta_r=0` 规范，所以其矩阵可能与名称矩阵相差一个共同自旋共轭；不能据逐元素不同误判为不同表示。连续族参数也应使用名称给出的规范参数，而不是原目录旧代表的参数值。

## 2. 查询、计算结果与导出

```python
from ssg_enumeration import (
    xiao_correspondences, from_xiao_label, load_standard_space_group,
    enumerate_ssg, label_for_record, save_catalog,
)

for row in xiao_correspondences(space_group=4):
    print(row.formal_label, row.category, row.our_label, row.xiao_label)

print(from_xiao_label("N143.5.2", formal=True))

group, metadata = load_standard_space_group(4)  # 需要可选依赖 spglib
result = enumerate_ssg(group, automorphisms="full")
for record in result:
    print(label_for_record(4, record))
save_catalog(result, "sg004_named.json", space_group=4)
```

带 `space_group` 的导出新增 `formal_label`、`category`、`catalogue_id`、`xiao_label`、`naming_version` 和 `hall_number`。为兼容旧程序，原 `record.label` 和旧 JSON 的 `label` 继续表示 17 类类型；正式展示使用 `record.name(number).text` 或 `formal_label`。不提供母群时，导出保持旧格式。

`label_for_record` 识别固定标准目录的全部已保存图册，以及其完整联合环面参数基的等价改写。它不声称识别任意原点、任意晶体基或任意自旋基下的输入。无法识别时明确报错；`name_for_chart(number, record)` 可给标准设定下的记录生成非目录规范的展示名称。

## 3. 文本记号与精确回算

文本用 `^{...}` 表示自旋上标，用 `_{(...)}` 表示平移分次波矢。示例：

```text
N: ^{(0,2*u0,0)}P 2_1 | u0 in R/Z; 2*C^T*k notin Z^3
P: ^{<2_x,1,1>}P 1
L: P 2/^{-1}m
```

第一个名称在螺旋操作上不重复显示分数平移带来的自旋角。其实际螺旋矩阵仍为 `Rz(2*pi*u0)`；波矢中 `2*u0` 的覆盖次数必须保留。域表达式中的 `C` 是本母群固定的 HNF 原胞矩阵，排除条件等价于原胞波矢 `2*q` 全部为整数。

`2_x` 表示绕自旋 x 轴半转，`m_z` 表示法向为 z 的镜面，`-1` 表示三维反演。一般旋转如 `3_[1,1,1]^2` 同时保留有向轴与旋转次数。尖括号中依次是三个 HNF 原胞平移的真转动像。P 使用 `diag(D,det(D))` 的保向提升，`embedded=False` 可取回原生二维矩阵。

```python
import json
from ssg_enumeration import SSGName, naming_setting

data = name.to_dict()  # JSON 兼容的精确数据，不含可执行对象
same = SSGName.from_dict(json.loads(json.dumps(data)))
setting = naming_setting(name.space_group)
print(setting["hall_number"], setting["primitive_basis"])
print(setting["atoms"])  # 每个 HM 原子的完整 Seitz 操作和截面分解
```

`parse_label` 解析正式文本，`SSGName.from_dict` 解析结构化数据。解析器只接受有限的精确算术语法，不执行输入中的 Python 代码。LaTeX 用于显示，不作为输入语法。

## 4. 母群操作表与规范代表

230 个母群沿用已有枚举的第一 Hall 设定。HM 方向遵循 Liu 补材 Tables S3–S9：四方为 `[001],[100],[110]`，三方/六方为 `[001],[100],[210]`，立方为 `[100],[111],[110]`。每个空间操作保留完整分数平移。

程序从原文提取 623 个代表操作，为每个母群联立求解同一个原点平移，使这些操作全部落入固定 Hall 母群。不能对不同操作分别挑原点。转换后保留原文代表；完整 HM 符号中比原文简写额外出现的冗余操作，取固定 Hall 数据库中同一方向的确定代表。所有 230 项均验证群归属和生成性，原点转换保存在 `liu_origin_shift_primitive`。

对每类已有的有限图册，先将完整 `(q,theta)` 联合环面规范化：用湮灭格行 HNF 定方程，逐坐标取最小偏移，保留限制后全部离散分量，再取饱和整数核的列 HNF。随后剥离轴向分数平移相位，固定共同反轴规范，在精确数据全序下选择代表。已有空间轨道和自旋规范决定候选范围；没有重新枚举空间自同构，也没有改变连续族合并规则。

因此这里的唯一性是**固定目录、固定命名版本内**的唯一性。任意合法输入的名称不一定已经是该目录的规范字符串；`to_xiao_label` 接受目录中的规范正式名称，不把任意同构符号字符串直接当成规范名称。

## 5. 验收与表格

完整对应表位于 `outputs/xiao_mapping/SSGclassify_Xiao_67475.xlsx`，第一列为正式名称，后面保留原来的八列，并增加 LaTeX 名称和 Hall 编号。行数仍为 67,475，包含 8,520 个连续族。L、P、N 数量分别为 1,421、9,542、56,512。

全量迁移由 `audits/naming/build_catalogue.py` 完成，验证记录保存在 `audits/naming/validation.json`。检查涵盖全部图册的精确截面回算、连续相位系数、平移协变及生成元关系、所有类的文本解析与“名称→记录→名称”、名称无重复、旧编号及 Xiao 对应关系不变。生成元与全部截面的乘法边检查给出有限群商的完整关系检验，不靠浮点采样。

这些是命名层面的精确验证；不会将历史 Xiao 对应中使用数值自旋基底求解、两组连续参数检查的结论升级为新的全参数等价证明。原有对应关系的适用范围仍见 [Xiao 对应说明](XIAO_LABEL_MAPPING_ZH.md)。

参考：[X. Chen et al., PRX 14, 031038 的补充材料，Tables S3–S9](https://journals.aps.org/prx/supplemental/10.1103/PhysRevX.14.031038/newSup_0724_v2.pdf)。
