# Scratch space

Put experimental code, test scripts, data dumps, and one-off notebooks here while you and Claude
are still working something out together. Nothing in this folder except this file is tracked by
git (see `.gitignore`), so you can delete anything under `einstein/` at any time without a git
operation.

This is the opposite of `artifacts/raw/`: `raw/` holds material Claude must never edit or delete.
Everything else in `einstein/` is disposable by default, and Claude may create, edit, or delete
files here freely while experimenting.

When an experiment works and becomes real work, move it to where it belongs: a script into
`scripts/`, a DAG into `dags/`, a decision into `artifacts/docs/claude-plan/` or
`artifacts/docs/concepts/`. Don't leave finished work sitting in `einstein/`.
