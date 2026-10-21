from __future__ import annotations

import pytest

from tinderbox.cli import Names, TinderboxError


def test_derives_every_spelling_from_a_hyphenated_name() -> None:
    names = Names.derive("photo-sorter")
    assert names.kebab == "photo-sorter"
    assert names.snake == "photo_sorter"
    assert names.upper == "PHOTO_SORTER"
    assert names.title == "Photo Sorter"
    assert names.identifier == "com.example.photosorter"


def test_single_word_name() -> None:
    names = Names.derive("offload")
    assert (names.snake, names.upper, names.title) == ("offload", "OFFLOAD", "Offload")
    assert names.identifier == "com.example.offload"


def test_digits_are_allowed_after_the_first_letter() -> None:
    names = Names.derive("app2-go")
    assert names.snake == "app2_go"
    assert names.title == "App2 Go"


def test_overrides_are_used_verbatim() -> None:
    names = Names.derive("photo-sorter", title="PhotoSorter Pro", identifier="org.acme.sorter")
    assert names.title == "PhotoSorter Pro"
    assert names.identifier == "org.acme.sorter"
    assert names.snake == "photo_sorter"


@pytest.mark.parametrize(
    "name",
    [
        "",
        "Photo",
        "photo_sorter",
        "-photo",
        "photo-",
        "photo--sorter",
        "1photo",
        "photo sorter",
        "ph/oto",
    ],
)
def test_invalid_names_are_refused(name: str) -> None:
    with pytest.raises(TinderboxError, match="invalid name"):
        Names.derive(name)


@pytest.mark.parametrize("title", ["", 'Say "hi"', "a\\b", "<b>", "A & B", "tab\there"])
def test_unsafe_titles_are_refused(title: str) -> None:
    with pytest.raises(TinderboxError, match="invalid title"):
        Names.derive("photo-sorter", title=title)


@pytest.mark.parametrize(
    "identifier", ["", "photo", "com..example", ".com.example", "com.exa mple", "com.example."]
)
def test_invalid_identifiers_are_refused(identifier: str) -> None:
    with pytest.raises(TinderboxError, match="invalid identifier"):
        Names.derive("photo-sorter", identifier=identifier)


def test_identifier_is_replaced_before_the_bare_kebab_form() -> None:
    names = Names.derive("photo-sorter")
    assert names.rename("com.example.emberly") == "com.example.photosorter"
    assert "photo-sorter" not in names.rename("com.example.emberly.helper")
    assert names.rename("com.example.emberly.helper") == "com.example.photosorter.helper"


def test_snake_and_upper_prefixes_are_replaced_before_the_title_and_kebab_forms() -> None:
    names = Names.derive("photo-sorter")
    text = "EMBERLY_HOME emberly_core Emberly emberly-core"
    assert (
        names.rename(text) == "PHOTO_SORTER_HOME photo_sorter_core Photo Sorter photo-sorter-core"
    )


def test_replacement_text_is_never_rescanned() -> None:
    names = Names.derive("photo-sorter", title="Emberly Fan", identifier="com.example.emberly.x")
    assert names.rename("Emberly com.example.emberly") == "Emberly Fan com.example.emberly.x"


def test_text_without_a_sentinel_is_unchanged() -> None:
    assert Names.derive("photo-sorter").rename("nothing here") == "nothing here"
