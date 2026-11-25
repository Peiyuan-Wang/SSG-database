# 公开接口与数据对象

所有下列函数均可从 `ssg_enumeration` 顶层导入。`help(function)` 可查看参数说明。

## 群输入

- `SpaceGroup(rotations, translations, name="custom")`：精确原胞 Seitz 代表。属性 `order, table, inverse, cocycle, reciprocal_rotations`。
- `from_generators(generators, name="custom", max_order=48)`：从 `(R,tau)` 生成元闭包构建。
- `group.multiply((t,a),(u,b))`：计算 `(t+R_a u+t_ab,ab)`。
- `group.validate_cocycle()`：验证完整 extension 2-cocycle 恒等式。
- `example_space_group(name)`：15 个预置例子。
- `space_group_from_number(number,hall_number=None)`：从可选 spglib 数据源取得 230 个标准母群之一，自动转换为精确原胞操作。
- `load_standard_space_group(number,hall_number=None)`：同时返回母群和来源信息（Hall setting、原胞基底、操作指纹等）。
- `standard_hall_numbers()`：每个国际编号采用第一个 Hall setting 的确定性映射。
- `primitive_operations(rotations,translations)`：用全平移格的 Hermite 基精确消除常规胞中心化。

批量接口 `from ssg_enumeration.census import run_census`，调用 `run_census(output,numbers=range(1,231),workers=4,resume=True)`。使用进程并行，脚本调用时放在 `if __name__ == '__main__':` 下。它对每个母群调用 `enumerate_ssg(...,automorphisms="full",verify=True)`，不读取外部 SSG 数据库。

## 精确线性代数

- `solve_gf2(M,b)` → `BinarySolution` 或 `None`；`.particular, .basis, .dimension, .count`，迭代得到全部解。
- `smith_decomposition(A)` → `(D,U,V)`，满足 `U*A*V=D`，包含幺模证书检查。
- `solve_torus(A,b=None,max_components=100000)` → 所有连通分量组成的 `tuple[AffineTorus]`。空 tuple 表示障碍无解。
- `AffineTorus(offset,basis)`：`x=offset+basis*u mod 1`。`.key, .constraints, .dimension, .parameter_count`；`.contains(x), .evaluate(u), .symbolic(prefix), .transform(F), .intersect(A,b)`。
- `parameter_relation(source,target,F=None)` → `ParameterRelation`，表示 `target(v)=F*source(u)`。
- `ParameterRelation.holds(u,v)`：有理参数精确验证；`.solution_components()` 求 `(u,v)` 的全部精确解族。

## 分级与有限群

- `enumerate_gradings(G)` → `tuple[Grading]`。每项 `.k, .bits, .signs`；`.evaluate(t,p)` 返回 ±1。
- `point_gradings(G)` → 所有 `eta∈Hom(P,Z2)`。
- `normal_subgroups(table)` → 正规子群列表；`quotient_group(table,H)` → 商表、投影。
- `find_isomorphism(source_table,target_table)` → 经完整乘法验证的一个同构，或 `None`。
- `rotation_group_catalog()` → 11 个允许的 SO(3) 有限像的表与精确矩阵。

## 枚举模块

`enumerate_noncoplanar_type0(G)`、`enumerate_noncoplanar_type1(G)`、`enumerate_noncoplanar_type2(G)` 分别输出三种非共面 rho；`enumerate_coplanar_type0(G)`、`enumerate_coplanar_type1(G,cached_type1=None)`、`enumerate_coplanar_type2(G)` 输出对应 O(2) 同态。

`solve_covariant_wavevectors(G,eta)` 包含零点，供下游分层；`solve_obstructed_1_cocycle(G,eta,k)` 对固定有理波矢返回已除连续 coboundary 的相位解；`solve_h1_eta(G,eta)` 为其零波矢齐次版本。保留相位的整体正负到后续自旋去重。

`invariant_kernel_vectors(G)`、`annihilator_trims(t0)`、`induced_permutations(G,ks)`、`solve_twisted_binary_cocycle(G,ks,perms,determinant_one=False)` 可独立用于 Type 2 计算。

## 表示与 SSG

- `MatrixRepresentation`：有限矩阵表示，`.translations` 三个晶格生成元矩阵，`.sections` 点群代表矩阵，`.kind, .image, .wavevectors, .kernel`；`.translation(t), .evaluate(t,p,embedded=False)`。
- `Type1Record`：`.eta, .torus, .stratum, .spin_dimension, .kind, .dimension, .parameter_count`。`.symbolic()` 返回 `(parameters,k,theta)`；`.parameters_at_wavevector(k)` 返回指定有理波矢的全部参数元组，保留不同相位分支；`.point(u)` 返回实际波矢与相位，检查排除域；`.evaluate(t,p,u)` 输出矩阵；`.inversion_relation()` 返回族内反号识别或 `None`；`.same_point(u,other,v)` 返回 `True/False`，极端精确实数表达式不可判定时为 `None`。
- `SSG(dimension,representation=None,grading=None)`：`.label/.type` 为 17 类编号，`.evaluate(t,p=0,parameters=(),embedded=True)` 输出包括 chi 的 varrho。共面默认嵌入 SO(3)，`embedded=False` 返回原生 O(2) 矩阵。
- `combine(rho,chi)`、`build_collinear_ssgs(gradings)` 供自行组织流程。

## 自同构与去重

- `SpaceGroupAutomorphism(A,phi,u,name)`：`.validate(G), .inverse(), .compose(other)`。
- `affine_automorphism(G,A,origin=(0,0,0),name="affine")`：从保向仿射坐标变换构造。
- `complete_automorphism_action(G)` → `CompleteAutomorphismAction(generators,certificate,scope)`：自动生成任意三维母群的完整保手征空间作用；`scope="full_out_plus"`。
- `point_normalizer_generators(rotations)`：完整整数点群正规化子及证书；`proper_linear_generators(generators)` 精确取行列式同态的核。
- `lattice_isometries(Q)`：由正定二次型精确椭球界枚举所有整系数等距矩阵及界。
- `p1_outer_generators(G)`：P1 完整 SL(3,Z) 生成元，保留兼容旧接口。
- `transform_grading, transform_representation, transform_ssg`：对指定数据做 pullback。
- `spin_key(ssg)`：**标准化内部枚举记录**的自旋等价键；不要用它比较任意旋转到非标准坐标的用户矩阵。任意实正交表示的同时共轭可用 `spin_equivalent_matrices(tuple_A,tuple_B)`。
- `deduplicate_spin_conjugation(records)` 后接 `deduplicate_automorphisms(records,automorphisms)`。直接调用后者时，调用方需先 `.validate(G)` 检查输入自同构；主函数自动检查。
- `equivalence_loci(ssg1,ssg2,alpha=None)`：在两个 Type 1 参数域之间求精确等价层。
- `stabilizer_loci(record,alpha=None,spin_sign=1)`：指定作用的稳定参数层。
- `verify_equivalence_witness(G,ssg1,u,ssg2,v,word=())`：验证给定有限自同构序列，支持精确无理参数。返回 `True` 是等价证据；`False` 仅否定该序列，不能解释为全局不等价；不可判定表达式返回 `None`。

## 主函数与结果

`enumerate_ssg(G,automorphisms=None,verify=True,progress=None)` → `EnumerationResult`。

`automorphisms="full"` 自动生成完整保手征空间作用，适用于所有三维母群；也可传 `CompleteAutomorphismAction`。旧选项 `automorphisms="p1_full"` 只适用于纯平移群；传 iterable 为按指定生成元作用的商。`verify=False` 仅跳过输出表示的关系检查，不改变数学算法；结果会标记 `verified=False`。

结果属性：

- `.charts`：自旋去重后的全部参数图册；关系索引引用这个序列。
- `.orbits`：空间自同构在图册上的轨道，每项是一组图册索引。
- `.records`、迭代器：每个图册轨道的一个代表，保留它的参数域。
- `.relations`：自旋反号、空间生成元及逆元的参数关系。
- `.spatial_scope`：`spin_only / provided_generators / full_out_plus / full_out_plus_P1`。
- `.normalizer_certificate`：自动完整算法的结构证书；未调用完整算法时为 `None`。
- `.by_label(label), .summary(), .locate(ssg)`。
- `.equivalent_points(i,u,j,v,max_states=10000)` → `EquivalenceDecision(status,reason,witness)`，其中状态为 `equivalent / distinct / unknown`。

关系中的 `.parameters.source*u + .parameters.target*v = .parameters.rhs mod 1`，`.ambient_map` 是从源 `(k,theta)` 到目标规范坐标的整数映射。

`save_catalog(result,path)` 输出完整 JSON 图册与关系；`catalog_dict(result)` 返回可序列化的 Python 字典。
