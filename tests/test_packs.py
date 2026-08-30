"""The pack boundary, now that there are two packs to hold it apart.

Until 30 August 2026 this file tested one pack, living in the same repository as
the loader that finds it — which means the interesting property, that a pack is
separable, had never been exercised. ``classification`` is the second pack, and
most of what is below is about what the loader may assume: that a pack declares
its own task classes, its own schema, its own metric set and its own rubric
library, and that adding a third one is a directory rather than a patch.
"""

from pathlib import Path

import pytest

# The same prose-aware leak check the boundary suite uses, imported rather
# than re-implemented so the two cannot disagree about what a leak is.
from tests.test_boundaries import _executable_text, _mentions

from langchef.core.design import OUTCOMES
from langchef.packs import discover, load, load_class, reporting, search_path, task_classes
from langchef.packs.manifest import OUTCOME_SHAPES, ManifestError, parse

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "langchef"

MINIMAL_CLASS = """
[task_classes.{cls}]
outcome = "predicted == ideal"
outcome_shape = "binary"
requires_judge = false
metrics = ["accuracy"]

[task_classes.{cls}.schema]
required = ["example_id", "predicted", "ideal"]
"""


def write_pack(root: Path, name: str, body: str = "", cls: str | None = None) -> Path:
    """A whole pack on disk: manifest, rubric library, nothing else required."""
    pack = root / name
    (pack / "rubrics").mkdir(parents=True)
    (pack / "rubrics" / "README.md").write_text("Empty on purpose.\n", encoding="utf-8")
    text = (
        f'[pack]\nname = "{name}"\nversion = "0.1.0"\n'
        f'application_class = "{name}"\ndescription = "A pack, for a test."\n'
    )
    text += body or MINIMAL_CLASS.format(cls=cls or name)
    (pack / "pack.toml").write_text(text, encoding="utf-8")
    return pack


def test_both_packs_resolve():
    names = {m.name for m in discover()}
    assert {"genai-rag", "classification"} <= names

    rag = load("genai-rag")
    assert rag.ref == "genai-rag@0.2.0"
    assert rag.application_class == "genai-rag"
    assert sorted(rag.task_classes) == ["generation", "qna"]

    classification = load("classification")
    assert classification.ref == "classification@0.1.0"
    assert sorted(classification.task_classes) == ["classification"]


def test_the_four_classes_split_exactly_where_the_decision_says_they_do():
    """DECISIONS.md #12: only a free-text target needs a judge."""
    judged = {tc.name for _, tc in task_classes() if tc.requires_judge}
    unjudged = {tc.name for _, tc in task_classes() if not tc.requires_judge}
    assert judged == {"qna", "generation"}
    assert unjudged == {"classification"}


def test_a_task_class_resolves_to_the_pack_that_declares_it():
    manifest, task_class = load_class("classification")
    assert manifest.name == "classification"
    assert task_class.requires_judge is False
    assert task_class.outcome.startswith("predicted == ideal")
    assert task_class.outcome_shape == "binary"
    assert task_class.required_fields == ("example_id", "input", "predicted", "ideal")
    assert "precision" in task_class.metrics and "recall" in task_class.metrics


def test_an_unknown_class_is_refused_with_the_ones_that_exist():
    with pytest.raises(ManifestError) as exc:
        load_class("summarisation")
    assert "summarisation" in str(exc.value)
    assert "classification" in str(exc.value)


def test_unknown_pack_raises_with_the_search_path_in_the_message():
    with pytest.raises(ManifestError) as exc:
        load("does-not-exist")
    assert "does-not-exist" in str(exc.value)
    assert str(search_path()[0]) in str(exc.value)


def test_manifest_requires_the_name_to_match_the_directory(tmp_path):
    pack = tmp_path / "mislabelled"
    pack.mkdir()
    (pack / "pack.toml").write_text(
        '[pack]\nname = "something-else"\nversion = "0.1.0"\n'
        'application_class = "x"\ndescription = "y"\n',
        encoding="utf-8",
    )
    with pytest.raises(ManifestError, match="!= directory"):
        parse(pack)


def test_manifest_reports_missing_fields(tmp_path):
    pack = tmp_path / "thin"
    pack.mkdir()
    (pack / "pack.toml").write_text('[pack]\nname = "thin"\n', encoding="utf-8")
    with pytest.raises(ManifestError, match="missing version"):
        parse(pack)


def test_a_pack_that_declares_no_task_class_does_not_resolve(tmp_path):
    """A pack that names no class cannot be applied to anything."""
    pack = write_pack(tmp_path, "classless", body="\n[contents]\njudges = []\n")
    with pytest.raises(ManifestError, match="no \\[task_classes"):
        parse(pack)


def test_a_class_must_say_whether_it_needs_a_judge(tmp_path):
    """The one field with no default: judged or hard target is the whole split."""
    body = (
        '\n[task_classes.mystery]\noutcome = "something"\noutcome_shape = "binary"\n'
        'metrics = ["accuracy"]\n'
        '\n[task_classes.mystery.schema]\nrequired = ["example_id"]\n'
    )
    pack = write_pack(tmp_path, "mystery", body=body)
    with pytest.raises(ManifestError, match="requires_judge"):
        parse(pack)


def test_a_class_must_declare_a_shape_the_core_can_actually_size(tmp_path):
    """`outcome_shape` is the only part of a class that reaches core/, so it is checked."""
    body = MINIMAL_CLASS.format(cls="ordinal").replace(
        'outcome_shape = "binary"', 'outcome_shape = "ordinal"'
    )
    pack = write_pack(tmp_path, "ordinal", body=body)
    with pytest.raises(ManifestError, match="outcome_shape"):
        parse(pack)


def test_the_declared_shapes_are_the_shapes_the_core_knows():
    """The mirror in the manifest and the vocabulary in the core cannot drift.

    ``core/design.py`` sizes the shapes it lists and refuses anything else, and it
    refuses by design rather than guessing (#68). The manifest mirrors that list
    instead of importing it, so this is what catches the day one of them grows a
    third shape and the other does not.
    """
    assert OUTCOME_SHAPES == OUTCOMES
    for _, task_class in task_classes():
        assert task_class.outcome_shape in OUTCOMES


def test_a_schema_without_the_pairing_key_is_refused(tmp_path):
    body = (
        '\n[task_classes.unpaired]\noutcome = "x"\noutcome_shape = "binary"\n'
        'requires_judge = false\nmetrics = ["accuracy"]\n'
        '\n[task_classes.unpaired.schema]\nrequired = ["predicted", "ideal"]\n'
    )
    pack = write_pack(tmp_path, "unpaired", body=body)
    with pytest.raises(ManifestError, match="example_id"):
        parse(pack)


def test_a_class_with_no_metrics_is_refused(tmp_path):
    body = (
        '\n[task_classes.silent]\noutcome = "x"\noutcome_shape = "binary"\n'
        "requires_judge = false\nmetrics = []\n"
        '\n[task_classes.silent.schema]\nrequired = ["example_id"]\n'
    )
    pack = write_pack(tmp_path, "silent", body=body)
    with pytest.raises(ManifestError, match="metrics is empty"):
        parse(pack)


def test_reporting_must_point_at_a_file_that_is_in_the_pack(tmp_path):
    body = MINIMAL_CLASS.format(cls="ghost").replace(
        'metrics = ["accuracy"]', 'metrics = ["accuracy"]\nreporting = "metrics.py:report"'
    )
    pack = write_pack(tmp_path, "ghost", body=body)
    with pytest.raises(ManifestError, match="does not exist"):
        parse(pack)


def test_a_listed_rubric_must_actually_be_in_the_library(tmp_path):
    """A rubric nobody declared is a rubric nobody reviewed, and the reverse."""
    body = MINIMAL_CLASS.format(cls="phantom") + '\n[contents]\nrubrics = ["missing.md"]\n'
    pack = write_pack(tmp_path, "phantom", body=body)
    with pytest.raises(ManifestError, match="listed but not in"):
        parse(pack)


def test_a_broken_pack_is_skipped_not_fatal(tmp_path, monkeypatch):
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "pack.toml").write_text("this is not toml {{{", encoding="utf-8")
    monkeypatch.setenv("LANGCHEF_PACK_PATH", str(tmp_path))
    assert "broken" not in {m.name for m in discover()}
    assert "genai-rag" in {m.name for m in discover()}


def test_every_pack_carries_a_rubric_library_and_an_empty_one_says_why():
    """An empty directory and unfinished work look identical. Prose separates them."""
    for manifest in discover():
        library = manifest.rubric_library
        assert library.is_dir(), f"{manifest.name} ships no rubrics/ directory"
        shipped = sorted(p.name for p in library.glob("*.md") if p.name != "README.md")
        assert shipped == list(manifest.rubrics), (
            f"{manifest.name}: rubrics/ holds {shipped} but the manifest declares "
            f"{list(manifest.rubrics)}"
        )
        if not shipped:
            assert (library / "README.md").is_file(), (
                f"{manifest.name}: an empty rubric library with no README is indistinguishable "
                "from an oversight"
            )


def test_a_pack_with_no_judged_class_ships_no_rubric():
    """The `classification` case: no judge, so nothing for a rubric to say."""
    for manifest in discover():
        if manifest.needs_a_judge:
            continue
        assert manifest.rubrics == (), (
            f"{manifest.name} declares no judged class but ships {manifest.rubrics}: "
            "either the rubric belongs in another pack, or a class here scores free text"
        )


def test_the_classification_pack_is_the_one_with_no_judge():
    classification = load("classification")
    assert classification.needs_a_judge is False
    assert classification.rubrics == ()
    assert not [p for p in classification.rubric_library.glob("*.md") if p.name != "README.md"]
    why = (classification.rubric_library / "README.md").read_text(encoding="utf-8")
    assert "requires_judge = false" in why


def test_a_third_class_is_a_directory_not_a_patch(tmp_path, monkeypatch):
    """The acceptance criterion, executed.

    A whole third pack — manifest, schema, metric set, rubric library and its own
    reporting code — is built in a temporary directory and put on the search
    path. Nothing is registered, nothing under ``src/`` is edited, and no name
    from it appears anywhere in the product.
    """
    body = (
        '\n[task_classes.ranking]\noutcome = "nDCG over the returned order"\n'
        'outcome_shape = "continuous"\nrequires_judge = false\nmetrics = ["ndcg"]\n'
        'reporting = "metrics.py:report"\n'
        '\n[task_classes.ranking.schema]\nrequired = ["example_id", "query", "returned"]\n'
        'optional = ["slices"]\n'
    )
    pack = write_pack(tmp_path, "ranking", body=body)
    (pack / "metrics.py").write_text(
        "def report(rows):\n    return {'task_class': 'ranking', 'n': len(list(rows))}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LANGCHEF_PACK_PATH", str(tmp_path))

    assert "ranking" in {m.name for m in discover()}
    manifest, task_class = load_class("ranking")
    assert manifest.path == pack
    assert task_class.metrics == ("ndcg",)
    assert task_class.required_fields == ("example_id", "query", "returned")

    # Its reporting runs, loaded out of the pack directory by the loader.
    assert reporting(manifest, task_class)([{"example_id": "1"}]) == {
        "task_class": "ranking",
        "n": 1,
    }

    # And the product has never heard of it. Checked over identifiers and string
    # literals only, never prose: `core/retrieval.py` explains that "order is the
    # ranking" while implementing nDCG, and forbidding the English word would push
    # authors into writing worse comments to satisfy a linter. The distinction is
    # the same one tests/test_boundaries.py draws, and for the same reason: a
    # docstring cannot make the product depend on a pack, but a string literal can,
    # because that is the raw material of a branch or a lookup.
    named = [
        f"{path.relative_to(SRC)}:{line}"
        for path in sorted(SRC.rglob("*.py"))
        for line, text in _executable_text(path)
        if _mentions(text, "ranking")
    ]
    assert named == [], f"the product names a pack-defined class: {named}"


def test_a_pack_earlier_on_the_search_path_shadows_a_class(tmp_path, monkeypatch):
    """First match wins, for classes as well as packs, so a local pack can override."""
    write_pack(tmp_path, "local-classification", cls="classification")
    monkeypatch.setenv("LANGCHEF_PACK_PATH", str(tmp_path))
    manifest, task_class = load_class("classification")
    assert manifest.name == "local-classification"
    assert task_class.metrics == ("accuracy",)
    # One winner per class name, not two.
    assert [tc.name for _, tc in task_classes()].count("classification") == 1


def test_reporting_refuses_a_class_that_declares_none():
    manifest, task_class = load_class("qna")
    assert task_class.reporting is None
    with pytest.raises(ManifestError, match="no reporting"):
        reporting(manifest, task_class)
