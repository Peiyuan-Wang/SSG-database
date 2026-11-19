# 与 Xiao 完整编号的逐项对应

本接口覆盖 230 个母空间群的 67,475 个分类：L 为 1,421，P 为 9,542，N 为 56,512。对应的是论文目录中的完整编号，例如 `N143.5.2`，不是仅对应表 I 的表示类型。

v0.4.0 已增加规则 v1.1 的正式 HM 自旋名称。对应表第一列现在展示正式名称；本文的 `SG...` 编号作为旧短编号保留，所有既有 Xiao 对应关系不变。使用 `name_for_label("N143.5.2").text`、`row.formal_label` 或 `from_xiao_label("N143.5.2", formal=True)` 取得新名称；详见 [正式名称接口](LABEL_USAGE_ZH.md)。

## 两侧标签

`N.1.2` 等 17 个标签是大类，不能唯一指定一个表示类。因此对既有计算目录增加完整标识 `SG143/N.1.2/0002`，依次表示母空间群、我们的类型、该母群该类型内从 1 开始的分类序号。序号按 `full_export_230_20261029` 的 `class_representatives` 顺序确定，只在这版目录内固定。改变枚举顺序时不能给旧编号重新赋义，应保留本表或提供版本迁移表。

`N143.5.2` 表示非共面、母空间群 143、论文表示类型 5、该类型内第 2 个分类。末尾序号取自原论文目录，通过表示匹配确定，不能由我们的枚举序号直接推算。

## 使用方法

在项目目录执行 `python -m pip install .`，或者安装本次 wheel。查询使用包内数据，不需要联网、spglib 或原先 8.65 GB 的枚举导出。

```python
from ssg_enumeration import (
    to_xiao_label, from_xiao_label, xiao_correspondences,
    xiao_mapping_metadata,
)

print(to_xiao_label('SG143/N.1.2/0002'))  # N143.5.2
print(to_xiao_label('N.1.2', space_group=143, class_index=2))  # N143.5.2
print(from_xiao_label('N143.5.2'))  # SG143/N.1.2/0002
for row in xiao_correspondences(space_group=143, category='N.1.2'):
    print(row.our_label, row.xiao_label, row.constituents)
print(len(xiao_correspondences()))  # 67475
print(xiao_mapping_metadata()['verification_scope'])
```

只传 `to_xiao_label('N.1.2')` 会报告标识不唯一，不会猜测编号。不存在的完整标识抛出 `KeyError`，错误的格式或范围抛出 `ValueError`。

查询返回不可变记录，包含双方完整编号、母群、我们的类型及序号、论文表示类型、ISO-IR 完整直和组成、连续参数个数，以及原目录轨道和代表图表的索引。最后两个索引从 0 开始。完整直和组成可能包含论文简写省略的平凡表示。

也可以查询重新计算出的标准目录代表（计算需安装 `'.[database]'`）：

```python
from ssg_enumeration import (
    load_standard_space_group, enumerate_ssg, xiao_label_for_record,
)
group, provenance = load_standard_space_group(143)
result = enumerate_ssg(group, automorphisms='full')
for record in result.records:
    print(record.label, xiao_label_for_record(143, record))
```

`xiao_label_for_record` 使用标准代表的完整序列化指纹。它不是任意基底、坐标、参数值或任意等价代表的通用识别器。不在表内的输入明确报错。可直接运行 [example_xiao_mapping.py](../example_xiao_mapping.py)。

## 对应示例

| 我们的完整编号 | Xiao 完整编号 |
|---|---|
| SG143/L.0.1/0001 | L143.1.1 |
| SG143/L.0.2/0001 | L143.2.1 |
| SG143/N.0.1/0001 | N143.4.1 |
| SG143/N.0.1/0002 | N143.1.1 |
| SG143/N.0.2/0001 | N143.10.2 |
| SG143/N.0.2/0002 | N143.9.1 |
| SG143/N.1.1/0001 | N143.3.1 |
| SG143/N.1.1/0002 | N143.4.2 |
| SG143/N.1.2/0001 | N143.5.1 |
| SG143/N.1.2/0002 | N143.5.2 |
| SG143/N.1.2/0003 | N143.5.3 |
| SG143/N.1.3/0001 | N143.2.1 |
| SG143/N.1.3/0002 | N143.10.1 |
| SG143/N.1.5/0001 | N143.11.1 |
| SG143/N.1.5/0002 | N143.11.2 |
| SG143/N.1.5/0003 | N143.11.3 |
| SG143/N.2.1/0001 | N143.16.1 |
| SG143/N.2.3/0001 | N143.16.2 |
| SG143/P.0/0001 | P143.1.1 |
| SG143/P.0/0002 | P143.4.1 |
| SG143/P.1.1/0001 | P143.3.1 |
| SG143/P.1.1/0002 | P143.4.2 |
| SG143/P.1.2/0001 | P143.5.1 |
| SG143/P.1.2/0002 | P143.5.2 |
| SG143/P.1.2/0003 | P143.5.3 |
| SG143/P.2.1/0001 | P143.2.1 |

完整表见 [SSGclassify_Xiao_67475.xlsx](../outputs/xiao_mapping/SSGclassify_Xiao_67475.xlsx)，包含全部逐项对应和 17 类汇总。

## 实际匹配步骤

1. 我方输入为既有完整计算目录中的表示图表和自同构商轨道。论文侧输入为 Xiao 的编号和不可约表示组成，用 ISO-IR 公式生成矩阵。没有用论文编号代替我方枚举。
2. 将常规胞变换到我方原胞，联立求解所有点群操作的原点平移同余条件，统一平移生成元和截面。非零原点修正逐群记录。
3. 共线表示比较符号分级。非共面表示先分离行列式分级，再按平移像比较有限点群表示核、带符号置换矩阵的共轭类，或共同不变轴上的平面转动相位。平面部分同时处理反射相位的规范自由度和整体相位反号。
4. 对连续表示，在完整联合变量（波矢和截面相位）上用整数零化子检验仿射环面同余，区分零波矢、非零 TRIM 和一般层。相位恢复到有理格点后，用整数运算检验，不能只比较波矢。
5. 论文代表可匹配我方任意图表，再按既有自同构轨道确定最终分类。不同最终轨道出现相同标准化索引时报冲突；每个论文编号必须唯一占据一个我方轨道。
6. 检验 67,475 个完整编号与论文 PDF 中提取的编号集合完全一致，各母群无遗漏或碰撞。对 8,520 个连续族，在第二组参数重新计算矩阵并要求仍落入原轨道。两组参数依次为 `(1,3,7)/101` 和 `(2,5,11)/101`。

逐群结果位于 `audits/xiao_mapping/results/sgNNN.json`。输入哈希、原点修正、阈值与覆盖范围见 [verification.json](../audits/xiao_mapping/verification.json)。`build_mapping.py` 实现匹配，`export_mapping.py` 校验计算目录哈希并生成包内索引和表格数据。

## 验证范围

本表提供全部目录条目的计算对应与唯一性检查。自旋基底求解使用浮点线性代数，矩阵阈值 `2e-8`。相位恢复到分母 `144×101` 的有理格点，按该分母放大后的恢复残差须小于 `1e-6`，再精确检验同余。因此，本次没有为每行生成全参数、全符号的共轭证明。

两组参数落入同一轨道是额外验证，不能单独推出任意参数值都满足同一符号关系。此前固定一般表示分支和完整 `(k,θ)` 联合环面的理论讨论见 [连续参数双向对应证明](XIAO_CONTINUOUS_EQUIVALENCE_PROOF_ZH.md)。本次不改变连续等价关系，也没有为凑齐论文条目数合并或拆分类。

更强的逐项符号证明需要保存并精确验证空间仿射变换、自旋共轭矩阵、连续参数仿射变换及特殊层的对应。本次计算匹配不能替代这一要求。

## 来源与版本

- Xiao 等，*Spin Space Groups: Full Classification and Applications*，Physical Review X 14, 031037，[DOI](https://doi.org/10.1103/PhysRevX.14.031037)。
- [APS 补充数据](https://journals.aps.org/prx/supplemental/10.1103/PhysRevX.14.031037) 中的 `O3_Rep_Class.zip`。
- [ISO-IR 表示数据库](https://iso.byu.edu/irtables.php)。本地来源文件记录公式、版本和源数据哈希。
- 我方基线 `full_export_230_20261029` 的源代码哈希保存在元数据中。新增查询模块后，当前包的整体哈希自然不同。
