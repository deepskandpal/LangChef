"""The decision memo.

The output of a run is a decision someone has to make, so the artifact is a memo
and not a leaderboard. A leaderboard shows which variant is ahead; a memo says
what was measured, how far the measurement can be trusted, what it implies, and
what it could not rule out.

The calibration section comes first and is not optional. A comparison produced
by an uncalibrated judge is confident garbage, and putting the agreement figures
above the result is the difference between a reader who knows that and one who
does not. Every number carries the run artifact it came from — the contract's
"no number without a run artifact", made visible rather than asserted.
"""

from datetime import UTC, datetime


def _pct(value: float) -> str:
    return "n/a" if value != value else f"{value:.1%}"


def _interval(payload: dict | None) -> str:
    if not payload or payload.get("lo") != payload.get("lo"):
        return "n/a"
    return f"[{payload['lo']:.1%}, {payload['hi']:.1%}]"


def _plain_interval(payload: dict | None) -> str:
    """Kappa is a coefficient on [-1, 1], not a rate. Percent signs would lie."""
    if not payload or payload.get("lo") != payload.get("lo"):
        return "n/a"
    return f"[{payload['lo']:.2f}, {payload['hi']:.2f}]"


def _trust(calibration: dict | None) -> tuple[str, str]:
    """A plain-English reading of the judge, and why."""
    if not calibration:
        return (
            "unknown",
            "This judge has never been checked against a person. Every number below "
            "inherits that uncertainty, and no decision should rest on them yet.",
        )
    kappa = calibration.get("kappa")
    n = calibration.get("n", 0)
    if kappa != kappa:
        return (
            "undefined",
            f"Agreement is undefined on these {n} labels — one rater never varied.",
        )
    if kappa >= 0.8:
        reading = "strong"
    elif kappa >= 0.6:
        reading = "usable"
    elif kappa >= 0.4:
        reading = "weak"
    else:
        reading = "not usable"
    return (
        reading,
        f"Cohen's kappa {kappa:.2f} on {n} human labels "
        f"(TPR {_pct(calibration.get('tpr', {}).get('value', float('nan')))}, "
        f"FPR {_pct(calibration.get('fpr', float('nan')))}).",
    )


def render(
    run_id: str,
    suite: str,
    comparison: dict | None = None,
    calibration: dict | None = None,
    taxonomy: dict | None = None,
    pin: dict | None = None,
    artifacts: dict[str, str] | None = None,
    when: datetime | None = None,
) -> str:
    """Build the memo. Sections with nothing to say are left out, not padded."""
    stamp = (when or datetime.now(UTC)).isoformat(timespec="seconds")
    artifacts = artifacts or {}
    reading, why = _trust(calibration)

    lines: list[str] = [
        f"# Decision memo — {suite}",
        "",
        f"`{run_id}` · {stamp}",
        "",
        "## Can this judge be trusted",
        "",
        f"**{reading}.** {why}",
        "",
    ]

    if calibration:
        confusion = calibration.get("confusion", {})
        lines += [
            "| | value | 95% interval | counts |",
            "|---|---|---|---|",
            f"| Agreement (kappa) | {calibration['kappa']:.2f} | "
            f"{_plain_interval(calibration.get('kappa_interval'))} | "
            f"n = {calibration.get('n', 0)} |",
            f"| Catches real problems (TPR) | {_pct(calibration['tpr']['value'])} | "
            f"{_interval(calibration['tpr'].get('interval'))} | "
            f"{calibration['tpr']['k']}/{calibration['tpr']['n']} |",
            f"| False alarms (FPR) | {_pct(calibration.get('fpr', float('nan')))} | — | "
            f"{confusion.get('fp', 0)}/{confusion.get('fp', 0) + confusion.get('tn', 0)} |",
            "",
        ]
        if artifacts.get("calibration"):
            lines += [f"Source: `{artifacts['calibration']}`", ""]

    if comparison:
        verdict = comparison.get("verdict", "inconclusive")
        headline = {
            "regression": "A regression. The variant is worse.",
            "improvement": "An improvement. The variant is better.",
            "inconclusive": "Inconclusive. This run cannot tell the two apart.",
        }[verdict]
        lines += [
            "## The result",
            "",
            f"**{headline}**",
            "",
            f"- Baseline pass rate: {_pct(comparison['baseline_rate'])}",
            f"- Variant pass rate: {_pct(comparison['variant_rate'])}",
            f"- Difference: {comparison['difference']:+.1%} "
            f"({_interval(comparison.get('interval'))})",
            f"- Paired goldens: {comparison.get('n', 0)}, "
            f"of which {comparison.get('discordant', 0)} changed verdict "
            f"({comparison['discordance']['broke']} broke, "
            f"{comparison['discordance']['fixed']} fixed)",
            f"- McNemar exact p = {comparison['p_value']:.4f}",
            "",
        ]
        if verdict == "inconclusive":
            lines += [
                f"This is a null result, not a clean bill of health: at this sample size the "
                f"smallest change the run could have detected is "
                f"{comparison.get('mde', float('nan')):.1%}. Anything smaller than that was "
                "never in reach, so 'no difference' here means 'no difference we could see'.",
                "",
            ]
        if artifacts.get("compare"):
            lines += [f"Source: `{artifacts['compare']}`", ""]

    if taxonomy and taxonomy.get("disagreements"):
        lines += ["## Where the judge and the human parted", ""]
        kinds = taxonomy.get("kinds", {})
        lines += [
            f"{taxonomy['disagreements']} of {taxonomy['n']} labelled examples disagreed — "
            f"{kinds.get('miss', 0)} missed problems, {kinds.get('false_alarm', 0)} false alarms.",
            "",
        ]
        for bucket in taxonomy.get("by_criterion", [])[:5]:
            lines.append(
                f"- **{bucket['label']}** — {bucket['disagreements']} of {bucket['total']} "
                f"({_pct(bucket['rate'])})"
            )
        separated = [c for c in taxonomy.get("concentrations", []) if c["separated"]]
        if separated:
            lines += ["", "Disagreement is concentrated, not spread:", ""]
            for c in separated[:3]:
                lines.append(
                    f"- `{c['dimension']} = {c['worst_value']}` disagrees "
                    f"{_pct(c['rate'])} of the time against a {_pct(c['base_rate'])} base rate "
                    f"({c['lift']:.1f}x, n = {c['n']})"
                )
        lines.append("")

    if pin:
        lines += [
            "## What produced these numbers",
            "",
            f"- Rubric: `{pin.get('rubric')}`",
            f"- Provider: `{pin.get('provider')}`",
            f"- Model: `{pin.get('cheap_model')}`"
            + (f", escalating to `{pin['strong_model']}`" if pin.get("strong_model") else ""),
            "",
            "A comparison across two different pins is two measurements, not a comparison. "
            "`langchef compare` exits 5 rather than rendering one.",
            "",
        ]

    lines += [
        "---",
        "",
        "*Generated by `langchef memo render`. Every figure above traces to a file "
        "under `runs/`; none of them were produced by a language model.*",
        "",
    ]
    return "\n".join(lines)
