Closes #

## What changed

<!-- One paragraph. What a reviewer needs to know before reading the diff. -->

## Checks

- [ ] `./scripts/verify.sh` — all 10 steps pass locally
- [ ] Any new statistic has a known-answer test against an independent implementation
- [ ] Generated files were regenerated, not hand-edited (`docs/*.html`, `docs/AGENT-CONTRACT.md`)
- [ ] No provider SDK is imported outside `src/langchef/judge/providers.py`
- [ ] If a rubric-scoring check changed, `VERSION` in `providers.py` was bumped
- [ ] If this settles a decision, `DECISIONS.md` has a new dated entry

## What I did not do

<!-- Scope left out, and why. An honest gap here is worth more than a tidy diff. -->
