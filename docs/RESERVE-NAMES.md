# Reserving the name

`langchef` is **available on PyPI** as of 30 August 2026. The authoritative
check is the JSON API, not the project page: `pypi.org/project/langchef/`
answers 200 for any name because Cloudflare serves a challenge page, so it tells
you nothing.

```sh
curl -s -o /dev/null -w '%{http_code}\n' https://pypi.org/pypi/langchef/json
# 404 = free, 200 = taken
```

GitHub already holds `deepskandpal/LangChef`. PyPI is the last name to claim.

## What only you can do

Publishing is wired to **Trusted Publishing**, so there is no API token to
create, paste into a secret, rotate, or leak. PyPI is told to trust this exact
repository and workflow, and GitHub mints a short-lived token per run. Setting
it up is four fields on a web form.

### 1. PyPI

Create the account at <https://pypi.org/account/register/> and **enable 2FA**,
which PyPI now requires before you can upload anything.

Then go to **Your account → Publishing → Add a pending publisher** and enter
exactly:

| Field | Value |
|---|---|
| PyPI Project Name | `langchef` |
| Owner | `deepskandpal` |
| Repository name | `LangChef` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

"Pending" is the right kind: it reserves the name for the first upload from that
workflow, so the project does not need to exist yet.

### 2. TestPyPI, optional but recommended

Same again at <https://test.pypi.org/>, with environment name `testpypi`. This
lets us rehearse the whole upload against a throwaway index before the real one,
which matters because **a PyPI upload cannot be replaced, only yanked.** A wrong
version number is permanent.

### 3. GitHub environments

Nothing to do unless you want a manual approval gate. If you do, create an
environment named `pypi` under **Settings → Environments** and add yourself as a
required reviewer. The workflow already targets it.

## What happens then

```sh
# rehearse against TestPyPI
gh workflow run release.yml -f target=testpypi

# the real thing: tag, push, done
git tag v0.1.0 && git push origin v0.1.0
```

The workflow runs `verify.sh` on both 3.12 and 3.13, checks the tag against the
version in `pyproject.toml` (a mismatch fails the build rather than publishing
the wrong number), runs `twine check --strict` on the metadata, and only then
uploads.

## Status

- [x] GitHub name held: `deepskandpal/LangChef`
- [x] `langchef` confirmed free on PyPI, 30 August 2026
- [x] `release.yml` wired for Trusted Publishing, both indexes
- [x] PyPI account and pending publisher created, 30 August 2026
- [x] **First release published: `langchef 0.1.0`, 30 August 2026**
- [x] Install instructions verified true: `uv run --with langchef langchef --version`
      resolves from PyPI and prints `langchef 0.1.0` in a clean environment

## Still open

TestPyPI has **no** pending publisher. The rehearsal run failed with
`invalid-publisher: valid token, but no corresponding publisher`, which is the
test index refusing a token GitHub minted correctly. That is a separate form on
<https://test.pypi.org> with environment name `testpypi`, and it is worth filling
in before 0.2.0: a PyPI upload cannot be replaced, only yanked, so the rehearsal
is the only place a version-number mistake is cheap.
