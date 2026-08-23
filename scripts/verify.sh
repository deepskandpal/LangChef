#!/usr/bin/env bash
# The whole check, in the order it runs everywhere.
#
# .github/workflows/ci.yml calls this script rather than repeating the steps,
# so a green run here is a green run there — there is no second list to drift.

set -uo pipefail
cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not on PATH. Install it, then re-run:" >&2
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi

pass=0
fail=0

step () {
  local label=$1
  shift
  printf '%-42s' "$label"
  local out
  if out=$("$@" 2>&1); then
    printf 'PASS\n'
    pass=$((pass + 1))
  else
    printf 'FAIL\n'
    printf '%s\n' "$out" | tail -25 | sed 's/^/    /'
    fail=$((fail + 1))
  fi
}

# The suite exercises the deterministic core and replays recorded judge
# responses. A provider key in this environment means a test could start
# spending money, so this runs first and stops nothing else from mattering.
smoke_wheel () {
  local wheel
  wheel=$(ls -t dist/*.whl 2>/dev/null | head -1) || return 1
  [ -n "$wheel" ] || return 1
  uv run --isolated --no-project --with "$wheel" langchef --version >/dev/null
}

step "1. no provider credentials present"  python3 scripts/assert_no_credentials.py
step "2. pinned interpreter (3.12)"        uv python install
step "3. dependencies match the lock"      uv sync --locked
step "4. lint"                             uv run ruff check .
step "5. format"                           uv run ruff format --check .
step "6. agent contract in sync"           uv run python scripts/render_contract.py --check
step "7. documentation site in sync"       uv run python scripts/build_docs.py --check
step "8. tests"                            uv run pytest
step "9. distribution builds"              uv build
step "10. wheel runs from a clean env"     smoke_wheel

printf '\n%d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ] || exit 1
