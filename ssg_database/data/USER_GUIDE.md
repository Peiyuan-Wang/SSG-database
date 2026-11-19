# Spin Space Group Database — User Guide

The Spin Space Group Database helps you find and examine spin space groups (SSGs) by their parent space group, magnetic configuration, translation properties, and spin-group structure. It contains 67,475 entries for the 230 crystallographic space groups: 1,421 collinear, 9,542 coplanar, and 56,512 noncoplanar entries. An entry describes either a discrete class or a continuous family.

## Getting started

The window has two areas: **Browse** and **Search** in the left sidebar, and the matching entries on the right.

To look up a known entry:

1. Select **Search** in the sidebar.
2. Enter an identifier such as `L5.2.2` under **Label search** and select **Search**.
3. Select **Details** in the result row, or double-click the row.
4. In the detail window, choose **Classification** for the classification fields or **Group operations** for matrices and operation symbols.

To explore a space group instead, select **Browse**, expand its number, and follow the classification tree. Selecting any branch shows the entries beneath it. The count beside a branch gives the number of entries it contains. Several detail windows can be open at the same time.

## Five-level classification

The Browse tree organizes SSGs in five levels. Individual SSG entries appear beneath the fifth level.

| Level | Classification | What it describes |
| --- | --- | --- |
| 1 | Parent space group | The crystallographic space group underlying the SSG. |
| 2 | Configuration | Whether the spin configuration is collinear, coplanar, or noncoplanar. |
| 3 | Spin-lattice type | One of 17 types describing the translation spin image and its grading. |
| 4 | Spin Bravais lattice | The translation spin structure, displayed using its wavevector representative or representatives. |
| 5 | Spin crystal class | The point-group image together with the relationship between translation and full spin images. |

The ordinary **Bravais lattice** describes the spatial translation lattice. The **Spin Bravais lattice** also describes the spin operations associated with translations.

### Configuration and spin-lattice type

The first letter of a spin-lattice type identifies the configuration: **L** for collinear, **P** for coplanar, and **N** for noncoplanar. The 17 types in the database are:

- Collinear: `L.0.1`, `L.0.2`.
- Coplanar: `P.0`, `P.1.1`, `P.1.2`, `P.2.1`, `P.2.2`.
- Noncoplanar: `N.0.1`, `N.0.2`, `N.1.1`, `N.1.2`, `N.1.3`, `N.1.4`, `N.1.5`, `N.2.1`, `N.2.2`, `N.2.3`.

The numbers distinguish translation-image types and their wavevector or grading cases. For example, `L.0.1` and `L.0.2` distinguish zero and nonzero grading wavevectors; `P.1.1` and `P.1.2` distinguish the special and general wavevector cases of the coplanar Type 1 layer. A type contains many SSG entries and is different from a Xiao ID.

### Group symbols

Let **G** be the parent space group, **T** its translation subgroup, and **P = G/T** the crystallographic point group. The effective spin representation is denoted by ϱ. In the noncoplanar convention, ϱ combines the spin representation with the grading χ.

- **H = ϱₜ(T)** is the image of the translation subgroup in spin space.
- **K = ϱ(G)** is the full effective spin image.
- **Q = K/H = ϱₚ(P)** is the point-group image after translation spin operations are factored out.
- **ker ϱₚ** contains the point operations whose spin images belong to H.

The displayed group symbols, such as C₂ or D₃, name abstract groups. Angle brackets, as in `⟨r(u₀), …⟩`, indicate a group described by generators. A fifth-level branch displays Q and K; different branches can share the same abstract group symbols when their spin-crystal structures differ.

## Reading an SSG entry

The results table contains:

| Column | Meaning |
| --- | --- |
| Configuration | Collinear, coplanar, or noncoplanar. |
| Spin-lattice type | The third-level type. |
| SSG name | The mathematical name of the SSG in the displayed setting. |
| Q and K | The point-group image Q and the effective spin image K. |
| Xiao ID | The catalogue identifier, for example `L5.2.2`. |
| Parameters | **Discrete**, **Continuous family**, or **Matched value**. |
| Details | Opens the entry's detail window. |

An **SSG name** combines the spatial group symbol with the relevant wavevector and spin-operation notation. A spin superscript such as 2_z denotes a half-turn about the spin z axis; m_z denotes reflection with normal along z. An overbar on 1 denotes the sign-reversing operation in the effective representation. Fractional spatial translations and the actual corresponding spin operations can be inspected in **Group operations**.

The **Xiao ID** identifies the corresponding entry in the classification of Zhenyu Xiao, Jianzhou Zhao, Yanqi Li, Ryuichi Shindou, and Zhi-Da Song, *Spin Space Groups: Full Classification and Applications*, Physical Review X **14**, 031037 (2024), [doi:10.1103/PhysRevX.14.031037](https://doi.org/10.1103/PhysRevX.14.031037).

## Browse and manage results

Select a tree branch to display its entries. The levels descend from the parent space group through configuration, spin-lattice type, Spin Bravais lattice, and spin crystal class. Expand or collapse branches with their arrows. **Settings → Show counts** controls the count column; **Settings → Automatic expansion level** controls how far a uniquely determined branch expands.

Above the result table, the condition chips show the active selection. Select a chip's × to remove that condition. The sidebar can be collapsed and reopened with the arrow button.

- **Fit columns** adjusts the result table to the available space; select it again to restore the earlier widths.
- **Compact matrix names** changes long matrix-containing names to a compact display. Select it again to show them in full; the full formula is also available in Details.
- Use **Previous**, **Next**, the page number, and **Rows per page** to navigate results.
- **Export results** saves all matching results to a CSV file, including results on other pages.
- Right-click a result for copy options or **Locate in Browse tree**.

## Search

The Search tab has two separate sections. **Label search** searches the identifier and name text. **Condition search** combines the selected fields; every populated condition must be satisfied. Use the Search button belonging to the section you want to run. **Reset** clears the fields in the search form.

### Condition search fields

| Field | How to use it |
| --- | --- |
| Space group | Enter or select a number from 1 to 230. Its Bravais lattice and crystallographic point group are filled automatically. |
| Bravais lattice | Select a spatial lattice such as `oP` or `mC`. Select this before entering wavevectors, or select a space group to fill it automatically. |
| Crystallographic point group | Select the point group of the parent crystal. |
| Configuration | Select collinear, coplanar, or noncoplanar. |
| Spin-lattice type | Select a third-level type such as `P.1.2`. |
| Parameter type | Select discrete entries or continuous families. |
| kχ | Enter the translation-grading wavevector. |
| k₁, k₂, k₃ | Enter rotational translation wavevectors, filling the fields in order. Multiple vectors are matched as an unordered set for discrete entries; a continuous wavevector family is matched using one rotational wavevector. |
| Q = ϱₚ(P) | Select the point-group image after factoring out H. |
| K = ϱ(G) | Select the full effective spin image for discrete SSGs. Selecting K restricts the search to discrete entries. |
| ker ϱₚ | Select the abstract group of point operations in the kernel. |

### Entering wavevectors

Enter each vector as three comma-separated rational components in **conventional reciprocal coordinates**, for example `0,0,1/2` or `0,0,1/3`. Use the coordinate setting associated with the selected parent space group or Bravais lattice. The search accounts for equivalent representatives and reciprocal-lattice periodicity in that setting. The grading wavevector kχ is a separate condition from the rotational wavevectors k₁, k₂, and k₃.

For a continuous family, a rotational wavevector matches when it belongs to the family's allowed wavevector domain, including its equivalent representatives. The result is the family entry. When a rotational wavevector is combined with Q or ker ϱₚ, the search checks the group condition on a compatible representative of that same wavevector. For a continuous family, this can produce a **Matched value**: the group image at that value can differ from the family's general value. **Classification** shows the compatible value and the corresponding group information, while the usual classification fields describe the catalogue entry. A search using kχ alone with group conditions uses the stored general or discrete group values.

### Search examples

**Find an entry by identifier.** Enter `L5.2.2` in Label search. Its result is collinear, belongs to space group 5, and has type `L.0.2`.

**Combine a wavevector and a group condition.** In Condition search, select space group `27`, configuration **Coplanar**, and spin-lattice type `P.1.2`. The Bravais lattice is set to `oP`. Enter `0,0,1/3` for k₁, select `C2` for Q, and select **Search**. The results include `P27.5.1` and `P27.5.2`. Open a result to examine its compatible value.

## Group details and operations

Each detail window is independent and can be resized, minimized, or maximized. The name is shown at the top. **Copy LaTeX** copies its LaTeX source; **Export JSON** saves the selected entry's data.

### Classification tab

This tab presents the parent space group, ordinary Bravais lattice, crystallographic point group, spin-lattice type, Spin Bravais lattice, H, K, Q, and ker ϱₚ. If the search identified a compatible representative, its matched wavevector, parameters, and group information appear here as well.

### Group operations tab

The table starts with the three primitive translation generators **T1–T3**, followed by one spatial representative for each point operation of the parent group. These representatives and the translation generators describe the space-group operations. Each row displays:

- the spin matrix;
- the spatial rotation matrix;
- the spatial translation vector;
- a spin-operation symbol;
- a space-operation symbol of the form `{R | t}`.

Use **Nontrivial spin**, **Trivial spin**, and **All elements** to choose which rows to display. Hover over a matrix to see its entries as text. The current filter is highlighted.

### Evaluating a continuous family

Continuous-family matrices initially contain parameters such as u₀ and u₁. Enter values in the order shown by the parameters, separated by commas, then select **Calculate**. Examples include `1/7`, `1/7,2/11`, `0.81`, and `sqrt(2)/10`.

Small-denominator rational inputs are evaluated exactly; decimals, larger-denominator fractions, and expressions such as `sqrt(2)/10` are evaluated numerically. The status above the table identifies exact or approximate matrices. Parameter-independent spin operations retain their symbols; a parameter-dependent approximate spin matrix is marked **Numerical matrix**. **Reset** restores the symbolic matrices.

A continuous-family entry describes its general parameter domain. Special parameter values can belong to a separate classification; evaluating a matrix does not change the catalogue classification fields. For a result with a matched representative, the initial operation table uses that representative and its spin frame. Entering parameters manually uses the parameterization of the displayed name; Reset returns to that symbolic form.
