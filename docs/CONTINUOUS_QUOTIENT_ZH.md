# 连续参数的分类与去重

与论文小群表示、实化及连续去重生成操作的完整理论对应见 [双向对应证明](XIAO_CONTINUOUS_EQUIVALENCE_PROOF_ZH.md)。注意非共面表示中论文二维块的波矢为 `κ=q+pχ`，不能在非平凡分级下将它直接等同于程序保存的 `q`。

> **2026-10-30 原文复核：** Xiao 等原论文允许一般表示沿完整分支经过特殊参数值延拓。固定一般表示数据的联合环面路径证明、原文定位和全部 230 群的精确证书见 [零波矢桥接证明](ZERO_BRIDGE_PROOF_ZH.md)。此前要求全程 `k≠0` 的 [核查](../audits/continuous_branches/REVIEW_ZH.md) 仅适用于更严格的删点路径关系，不构成论文规则下的反例。

**连续延拓口径：同一完整联合解环面的一般部分计一族，路径允许经过该分支的特殊化。** 不任意拼接不同联合分量；特殊点仍按其实际类型单列，族内部保留具体参数点的精确等价关系。

## 三种问题必须分开

**同一解族的两种写法。** `k=(u,2u,0)` 与 `k=(-2v,-4v,0)` 的像是同一子环面，不能因基底或参数周期的写法不同重复列出。

**同一族内两个不同群。** 对纯平移群，`k=(1/3,0,0)` 与 `k=(1/4,0,0)` 都属于三维一般波矢族，但平移像的阶分别为 3、4，绝不等价。

**空间自同构导致的参数识别。** 在 P1 中，`k=(1/3,0,0)` 与 `k=(0,1/3,0)` 在 SL(3,Z) 下等价。需要同时变换 rho 与 chi，不能独立给二者各取最小代表。

这三层分别由 `AffineTorus.key`、`Type1Record.same_point` 和 `EnumerationResult.relations/equivalent_points` 处理。

## 一、精确解空间

采用 turns 单位，令 `x=(q1,q2,q3,theta_0,...,theta_(n-1))`。

联合约束为：

```
(R_p^T - eta_p I) q = 0                    mod Z³
theta_a + eta_a theta_b - theta_ab - q·t_ab = 0  mod Z
theta_r = 0   （存在 eta_r=-1 时的规范固定）
```

所有系数均为整数。先用 Hermite 标准形压缩**整数行格**，再作 `UAV=D` Smith 分解。不能用有理数行简化代替整数行格操作：`2x=0 mod 1` 有两个解，而把行除以 2 会错误删去一个。

每个解分量表示为 `x=x0+B u mod 1`，`x0` 为有理向量，`B` 为整数矩阵，`u∈(R/Z)^d`。U、V 的幺模性及乘法证书会被检查。出现显式资源上限时抛出错误，不返回未注明的截断结果。

## 二、同一子环面的标准形式

对 `B` 求整数零化子

`L_B={ell∈Z^N: ell^T B=0}`。

给 `L_B` 的基作 Hermite 标准形，得到确定的 `C`。子环面恰是

`C x = C x0 mod 1`。

所以 `(C, Cx0 mod 1)` 是与参数命名、整基变换和有限覆盖无关的精确键。一个参数族是否相等不需要抽点。

## 三、自旋商

eta 非平凡时先除去连续相位共轭；之后 Type 1 的剩余自旋作用是 `x -> -x`。若它交换两张不同图册，只保留其中一个代表；若它保持同一图册，就必须保留族内识别：

`B u + B v = -2 x0 mod 1`。

“留下一个族”并不等于“这个族只剩一个参数点”。函数 `inversion_relation()` 给出这条精确关系，`same_point(u,other,v)` 判定特定参数值是否相差整体自旋共轭。

## 四、空间商与原点平移

`automorphisms="full"` 通过 [完整算法](NORMALIZERS_ZH.md) 自动生成完整空间作用；也可手动输入。自同构写作

`alpha(t*s(p))=(A t+u_p)*s(phi(p))`，`det A=+1`。

在 Type 1 坐标上：

```
q'       = A^T q
eta'_p   = eta_phi(p)
theta'_p = theta_phi(p) + q·u_p
```

然后重新固定 eta′ 的相位规范。这个过程是一个整数线性映射 `x'=F_alpha x mod 1`。分级同时变换：

```
kchi' = A^T kchi mod Z³
bit'_p = bit_phi(p) + 2 kchi·u_p mod 2
```

原点平移即使不改波矢，也可能改变 section 相位或分级，所以只比较波矢轨道会误并。

源族 `x0+B u` 与目标族 `y0+C v` 的等价关系为

`F_alpha B u - C v = y0-F_alpha x0 mod 1`，

并允许整体自旋反号。每条关系有源/目标图册编号和精确矩阵，保存在 `result.relations` 中。

## 五、特殊层与稳定子

零波矢和非零 TRIM 是 Type 与标签改变的层，枚举时必须分开。一般域显式排除 `2q∈Z³`，避免特殊点混入一般层。

对于一个指定自同构，稳定点满足 `(±F-I)(x0+B u)=0 mod 1`，由 `stabilizer_loci` 精确求解。比如 P1 的纯自旋反号固定点是八个 TRIM，正好全在一般域的排除集合中。

`stabilizer_loci` 给出指定作用的固定层；`equivalence_loci` 给出两张图册之间的参数等价层。返回层须与源、目标的排除条件同时使用。程序不声称通过有限个生成元的固定层就枚举了无限群全部稳定子类型。

## 六、无限 Out⁺ 的处理边界

P1 已有无限空间外自同构群 `SL(3,Z)`。它在波矢环面上不是一个有限点群，不能只用某个有限多面体和少数旋转替代。

本包给出精确的**生成元商关系表示**：有限图册目录、图册轨道、生成元及逆元的参数关系。这是完整的商空间描述方式，但不是所有无理轨道的一键规范代表算法。

对指定有理参数，整数变换保持公共分母，所以轨道有限；`equivalent_points` 逐步寻找证据，并在完整穷尽轨道后才报告不等价。设置 `max_states` 防止巨大分母耗尽资源，达到限制返回 `unknown`。

对一般无理参数，可做精确求值和直接自旋等价检验；没有找到空间轨道证据时返回 `unknown`，不把“未找到”当作“不存在”。`verify_equivalence_witness(G,s1,u,s2,v,word)` 可以验证指定有限空间自同构序列，包括无理参数的证据。需自动判定更多无理点的空间等价时可直接使用保存的符号关系，或添加特定母群的数论判据。

P1 的单独有理波矢还有快速完整判据：SL(3,Z) 轨道由 `k mod Z³` 的加法阶确定，即三个有理坐标分母的最小公倍数，见 `rational_p1_wavevector_orbit_key`。有非平凡 chi 或额外 section 数据时，这个单独波矢判据不能替代联合轨道比较。

## 七、可运行例子

```python
from sympy import Rational as Q
from ssg_enumeration import *

G = example_space_group("P1")
result = enumerate_ssg(G, "full")
s = result.by_label("P.1.2")[0]
i = result.locate(s)

assert result.equivalent_points(i,[Q(1,3),0,0],i,[0,Q(1,3),0]).status == "equivalent"
assert result.equivalent_points(i,[Q(1,3),0,0],i,[Q(1,4),0,0]).status == "distinct"
assert result.equivalent_points(i,[Q(1,31),0,0],i,[Q(1,29),0,0],max_states=2).status == "unknown"

fixed = stabilizer_loci(s.representation, spin_sign=-1)
assert len(fixed) == 8
```
