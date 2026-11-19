# Windows Codex Task: Verify and Package v0.9.7

## Objective

Check the current v0.9.7 source changes on Windows, fix any Windows-specific problems, and produce a new, runnable Windows build. Do not treat the earlier v0.9.7 package as released: it is tentative and must not be reused as the new build.

The Mac and Windows apps must use the same classification framework, data meanings, English UI, and interaction behavior. This task is about verifying and packaging the shared UI on Windows; do not redesign the classification scheme or change scientific records to make a display issue disappear.

## Source and database

- Work from the latest project source in this repository, including the current changes in `ssg_enumeration/desktop.py`, `ssg_enumeration/naming.py`, and the relevant tests.
- Use the corrected database at `output/retrieval/v097-space-fixed/SSGclassify.sqlite` as the source for the Windows package. The earlier `output/retrieval/v097/SSGclassify.sqlite` still contains incorrectly displayed space-group overbars. Do not silently substitute an older database or an older `SSGclassify-spinnames.sqlite` file. If the Windows build requires a separate spin-name database, identify its role and update it from the same latest source before packaging.
- Verify that the database bundled inside the final Windows build is the database you intended to package, not merely the database present in the working tree.
- Keep the UI in English.

## Required checks

Record **Pass**, **Fail**, or **Not verified** for every numbered item. Include the Windows version, Python version, Qt binding/version, build command, and the path/name of the tested executable.

### 1. Overbars in SSG names

- Inspect names containing overbarred numbers and symbols in Browse, search results, and the Details view.
- Confirm bars render above and centered over the intended symbol. They must not appear as minus signs, ordinary hyphens, misplaced bars, or bars over neighboring characters.
- Include examples that exercise both generated names and formulas loaded from the packaged database.
- Check at normal Windows display scaling and at a non-100% scaling setting if available.

### 2. Text clarity and font consistency

- Inspect the Browse tree, search controls, result table, mathematical labels, and Details view.
- Confirm text and math glyphs are sharp and legible at the default window size and Windows display scaling.
- Check that letters, digits, Greek symbols, subscripts, and superscripts use the intended consistent font treatment and are not substituted with missing-glyph boxes.
- Resize the window and confirm text does not become clipped or blurry.

### 3. Matrix delimiters and entries

- Open a group with spatial-operation matrices and inspect the delimiters at several matrix heights.
- Confirm parentheses are balanced, have a consistent stroke, scale with the matrix, and resemble proper mathematical delimiters rather than thick hand-drawn arcs.
- Check representative entries including `sqrt(3)`, `-sqrt(3)/2`, `-1/2`, and integer values. The radical must render as √, and negative fractions must use the same stacked-fraction layout as positive fractions.
- Confirm matrix content is not clipped at the row or window boundary.

### 4. Group-operation filters

On the group-operation Details page, verify all three controls:

- **Nontrivial spin** shows exactly elements whose spin operation is not the identity.
- **Trivial spin** shows exactly elements whose spin operation is the identity.
- **All elements** restores the complete element list.

Check that changing filters does not alter the group data, row labels, translation generators, or other Details tabs. If a status/count is shown, verify it agrees with the visible rows.

### 5. Browse-tree hierarchy

- Expand at least three nested levels in the Browse tree.
- Confirm each level has its own expand/collapse arrow and clear indentation relative to its parent.
- Items at the same level must align with each other; child levels should be indented. Parent level-one labels must remain aligned in their own column.
- Check both expanded and collapsed states, scrolling, and a resized/narrow window. No level should lose its arrow or collapse into the parent's alignment.

### 6. Duplicate `O` and `T` choices

- Open the `K = ρ(G)` selector in Condition Search.
- Confirm `O` appears once and each genuinely distinct `T` entry appears once. Do not remove distinct groups merely because their glyph is the same; compare the underlying group identifiers and intended choices.
- Select the entries and verify the resulting search condition uses the correct group identity.
- Confirm typing into the selector does not create duplicate ad-hoc entries.

### 7. Radical and fraction rendering

- In the matrix view, confirm `sqrt(3)` is shown as √3, not the literal string `sqrt(3)`.
- Confirm `1/2` and `-1/2` use the same stacked fraction format, with the sign attached to the numerator.
- Check the same rendering in all available matrix contexts, including the default matrices and matrices after continuous-parameter calculation.

### 8. Initial page

- Start the packaged executable with a clean user configuration and confirm it opens on **Browse**, not **Search**.
- Close and reopen it to ensure the initial page is still Browse unless the product intentionally persists a user-selected page. If the page is persisted, document and verify the intended behavior.

## Windows runtime and packaging checks

- Build a fresh Windows artifact from the current source using the repository's Windows build procedure. Do not copy or rename an older executable and call it new.
- Run the packaged executable, not only `python run_desktop.py`.
- Run the repository's available launch/smoke checks on the packaged build. Confirm the bundled database loads and reports 67,475 classes, 230 parent groups, and 67,475 formulas.
- Verify that the app can open Browse, search for a known Xiao ID, open Details, show group operations, and close without an error dialog.
- Confirm the final package contains the expected Qt runtime and database, and launches on a Windows machine without requiring a development Python environment.
- If practical, test on a clean Windows account or machine. Record any prerequisites if this cannot be done.

## Evidence to return

Provide a short report with:

1. The Pass/Fail/Not verified result for checks 1–8 and the packaging checks.
2. Screenshots of: Browse with multiple expanded levels; an overbarred SSG name; a matrix containing √3 and stacked fractions; and each of the three group-operation filter states.
3. The exact build command and tested executable path.
4. The database file bundled in the executable, its size, and its class/parent/formula counts.
5. Any source changes made, with file names and a brief reason.
6. Any failed or unverified check. Do not describe an unverified item as fixed.
7. The final Windows package path and SHA-256 checksum.

Do not publish or upload the Windows build to GitHub as part of this verification task. Return the verified artifact and report for review first.
