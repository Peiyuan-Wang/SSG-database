# Naming migration audit

The input is the existing exact `full_export_230_20261029` catalogue. This audit
does not run a new SSG census and does not alter the Xiao matching assignments.

The migration scripts use the installed package, SymPy 1.14, spglib and ijson.
The workbook reader uses openpyxl for read-only validation; spreadsheet authoring
uses `@oai/artifact-tool` in the documented workspace runtime.

1. `extract.py` streams charts and orbits into `tmp/naming_rule/catalogues`.
2. `read_liu_operations.py` reads the layout-preserving text extraction of Liu's
   PRX 14, 031038 supplement. Its 623 displayed Seitz operations are saved in
   `liu_operations.json`; these factual operations are included here.
3. `build_settings.py` solves a common exact origin transformation per parent,
   checks all references and the full HM generating set, then freezes 230 settings.
4. `build_catalogue.py` checks every chart, chooses each orbit's formal name,
   checks independent text parsing and exact record recovery, and packages the
   names and lookup aliases. Checkpoints include a settings and source hash.
5. `verify_catalogue.py` uses the public parser for all 67,475 names, checks
   recovered categories and every chart alias, and writes `validation.json`.
6. `prepare_table.py` joins names to the original correspondence row order.
   `update_table.mjs --inspect` renders the source workbook; running it without
   that flag adds the three naming columns. This is a one-time migration from
   the original eight-column workbook, not an idempotent append operation.
7. `verify_workbook.py` reads the exported workbook and compares every old and
   new cell, the 67,475-row coverage, summary formulas/totals, filter and panes.

The original input workbook is preserved under `tmp/naming_rule/original.xlsx`
in the development workspace. For a rerun, use that input rather than feeding
the already migrated eleven-column workbook into step 6.

Exact naming verification does not upgrade the historical Xiao matching's
numerical intertwiner and two-parameter checks into a new symbolic equivalence
proof. See `docs/XIAO_LABEL_MAPPING_ZH.md` for that separate scope.
