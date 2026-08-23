# Reserving the name

The last open M0 item. Everything here touches an account and is outward-facing,
so it needs your hands rather than an agent's. The distribution is already
built and verified — `uv build` produces `dist/langchef-0.1.0-py3-none-any.whl`
and it runs from an isolated environment — so these are the only steps left.

## 1. GitHub

The 1.0 repository currently owns `deepskandpal/langchef`. Rename it first, then
create the new one. Renaming leaves a redirect in place, so nothing already
cloned breaks.

```sh
gh repo rename langchef-legacy --repo deepskandpal/langchef
gh repo edit deepskandpal/langchef-legacy --description "LangChef 1.0 — the eval platform. Archived; see deepskandpal/langchef."
gh repo archive deepskandpal/langchef-legacy

cd ~/code/github/langchef
gh repo create deepskandpal/langchef --private --source=. --remote=origin --push
```

The local working copy of 1.0 has already been moved to
`~/code/github/langchef-legacy`; its `origin` still points at the old URL and
will follow the rename automatically.

Keep the new repository private until the gate clears. It goes public with the
open-core split, not before.

## 2. PyPI

Reserving a name on PyPI means uploading a release; there is no other
mechanism. Upload `0.1.0` to TestPyPI first, confirm it installs, then upload
the real one.

```sh
uv build
uv publish --index testpypi        # confirm, then:
uv publish                         # needs a PyPI API token in UV_PUBLISH_TOKEN
```

`0.1.0` is a pre-alpha placeholder and is classified as such in
`pyproject.toml`. Yanking it later is fine; losing the name is not.

## 3. The skills registry

Reserve `langchef` as a skill name when the Claude Code plugin is packaged in
M4. Nothing to publish before then — note the intent and check the name is still
free at the start of M4.

## Verification

```sh
gh repo view deepskandpal/langchef --json name,visibility,isArchived
pip index versions langchef
```
