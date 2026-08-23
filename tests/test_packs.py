"""The pack boundary works from the first commit, with exactly one pack."""

import pytest

from langchef.packs import discover, load, search_path
from langchef.packs.manifest import ManifestError, parse


def test_the_only_pack_resolves():
    names = {m.name for m in discover()}
    assert "genai-rag" in names

    pack = load("genai-rag")
    assert pack.ref == "genai-rag@0.1.0"
    assert pack.application_class == "genai-rag"


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


def test_a_broken_pack_is_skipped_not_fatal(tmp_path, monkeypatch):
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "pack.toml").write_text("this is not toml {{{", encoding="utf-8")
    monkeypatch.setenv("LANGCHEF_PACK_PATH", str(tmp_path))
    assert "broken" not in {m.name for m in discover()}
    assert "genai-rag" in {m.name for m in discover()}
