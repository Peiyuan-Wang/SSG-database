# Desktop interface review — 0.9.0

The requested items were checked against the implemented desktop application and its tests:

1. The interface uses Arial/Helvetica rather than Georgia's old-style figures. Parent-group text uses lining digits; mathematical subscripts remain subscripts.
2. Q and K table headings are compiled by the same LaTeX toolchain and drawn at the same scale.
3. The base scale for compiled SSG names is 2.2 rather than 3.0; names keep a common scale regardless of their width or bounding box.
4. Browse and Search occupy the left sidebar, next to the result table. Settings remains in the application menu, not as a sidebar button.
5. Every result row has its own Details button. Tests select a nonfirst row and also exercise a matched continuous specialization.
6. The Search sidebar shows the separate Label search above the condition form, with the complete set of prior filters available by scrolling.
7. Classification details hide the Hall number, present Bravais lattice and point group in distinct columns, typeset the image labels with mathematical subscripts, and place the subdued continuous-family notice after the data. The fixed Hall setting remains in the database and exported exact data.
8. Matrix brackets are rendered as thin vector curves instead of enlarged font glyphs.
9. Combining overlines in parent-group and operation displays are rendered on their own glyphs. Spin rotoinversions previously written as -3, -4, or -6 are typeset with an overbar. The separately rebuilt database corrects 3,278 names across 165 parent groups; all 3,278 were regenerated independently from the naming code and compared. All 67,475 formula hashes and vector resources were read back, and the classification records and other catalogue tables were compared with the previous database. Representative screens were visually inspected; this is not a claim of manual visual inspection of every formula.

No classification, equivalence rule, numerical representation, or Xiao identifier was changed. The new database differs in the display LaTeX and corresponding SVG resources for those 3,278 entries.
