# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for navigation table module."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from unittest import mock

import pytest

from src import discourse, exceptions, navigation_table, types_
from src.exceptions import NavigationTableParseError

from .helpers import assert_substrings_in_string


@pytest.mark.parametrize(
    "line, expected_result",
    [
        pytest.param("", True, id="empty"),
        pytest.param("unmatched line", True, id="does not match any line regex"),
        pytest.param("||||", True, id="line with nothing"),
        pytest.param("|level|path|navlink|", True, id="matches the header lower case"),
        pytest.param("|LEVEL|PATH|NAVLINK|", True, id="matches the header upper case"),
        pytest.param("|Level|Path|Navlink|", True, id="matches the header mixed case"),
        pytest.param(" |level|path|navlink|", True, id="matches the header single leading space"),
        # This test ensures that the whitespace check includes looking for multiple spaces, needed
        # only once since the same regular expression is used for all whitespace checks
        pytest.param(
            "  |level|path|navlink|", True, id="matches the header multiple leading space"
        ),
        # This test ensures that the whitespace check includes looking for tabs, needed only once
        # since the same regular expression is used for all whitespace checks
        pytest.param("\t|level|path|navlink|", True, id="matches the header leading tab"),
        pytest.param("| level|path|navlink|", True, id="matches the header space before level"),
        pytest.param("|level |path|navlink|", True, id="matches the header space after level"),
        pytest.param("|level| path|navlink|", True, id="matches the header space before path"),
        pytest.param("|level|path |navlink|", True, id="matches the header space after path"),
        pytest.param("|level|path| navlink|", True, id="matches the header space before navlink"),
        pytest.param("|level|path|navlink |", True, id="matches the header space after navlink"),
        pytest.param("|level|path|navlink| ", True, id="matches the header trailing space"),
        pytest.param("|-|-|-|", True, id="matches filler single dash"),
        pytest.param("|--|--|--|", True, id="matches filler multiple dash"),
        pytest.param(" |-|-|-|", True, id="matches filler leading space"),
        pytest.param("| -|-|-|", True, id="matches filler space before first column"),
        pytest.param("|- |-|-|", True, id="matches filler space after first column"),
        pytest.param("|-| -|-|", True, id="matches filler space before second column"),
        pytest.param("|-|- |-|", True, id="matches filler space after second column"),
        pytest.param("|-|-| -|", True, id="matches filler space before third column"),
        pytest.param("|-|-|- |", True, id="matches filler space after third column"),
        pytest.param("|-|-|-| ", True, id="matches filler trailing space"),
        pytest.param("||a|[a]()|", True, id="first column empty"),
        pytest.param("|a|a|[a]()|", True, id="first column character"),
        pytest.param("|1||[a]()|", True, id="second column empty"),
        pytest.param("|1|/|[a]()|", True, id="second column forward slash"),
        pytest.param("|1|a||", True, id="third column empty"),
        pytest.param("|1|a|a]()|", True, id="third column leading square bracket missing"),
        pytest.param("|1|a|[]()|", True, id="third column title missing"),
        pytest.param("|1|a|[a()|", True, id="third column closing square bracket missing"),
        pytest.param("|1|a|[a])|", True, id="third column opening link bracket missing"),
        pytest.param(r"|1|a|[a](\)|", True, id="third column link includes backslash"),
        pytest.param("|1|a|[a](|", True, id="third column closing link bracket missing"),
        pytest.param("|1|a|[a]()|", False, id="matches row"),
    ],
)
def test__filter_line(line, expected_result):
    """
    arrange: given line and expected return value
    act: when _filter_line is called with the line
    assert: then the expected return value is returned.
    """
    returned_result = navigation_table._filter_line(line)

    assert returned_result == expected_result


@pytest.mark.parametrize(
    "line, expected_result",
    [
        pytest.param("|1|a|[b]()|", (1, ("a",), ("b", None)), id="simple"),
        pytest.param(" |1|a|[b]()|", (1, ("a",), ("b", None)), id="simple leading space"),
        pytest.param(
            "| 1|a|[b]()|", (1, ("a",), ("b", None)), id="simple space before first column"
        ),
        pytest.param(
            "|1 |a|[b]()|", (1, ("a",), ("b", None)), id="simple space after first column"
        ),
        pytest.param(
            "|1| a|[b]()|", (1, ("a",), ("b", None)), id="simple space before second column"
        ),
        pytest.param(
            "|1|a |[b]()|", (1, ("a",), ("b", None)), id="simple space after second column"
        ),
        pytest.param(
            "|1|a| [b]()|", (1, ("a",), ("b", None)), id="simple space before third column"
        ),
        pytest.param(
            "|1|a|[b]() |", (1, ("a",), ("b", None)), id="simple space after third column"
        ),
        pytest.param("|1|a|[b]()| ", (1, ("a",), ("b", None)), id="simple trailing space"),
        pytest.param("|12|a|[b]()|", (12, ("a",), ("b", None)), id="first column multiple digits"),
        pytest.param(
            "|1|az|[b]()|", (1, ("az",), ("b", None)), id="second column multiple characters"
        ),
        pytest.param("|1|A|[b]()|", (1, ("A",), ("b", None)), id="second column upper case"),
        pytest.param("|1|2|[b]()|", (1, ("2",), ("b", None)), id="second column digit"),
        pytest.param("|1|_|[b]()|", (1, ("_",), ("b", None)), id="second column underscore"),
        pytest.param("|1|-|[b]()|", (1, ("-",), ("b", None)), id="second column dash"),
        pytest.param(
            "|1|a|[bz]()|", (1, ("a",), ("bz", None)), id="third column title multiple characters"
        ),
        pytest.param(
            "|1|a|[B]()|", (1, ("a",), ("B", None)), id="third column title capital character"
        ),
        pytest.param("|1|a|[2]()|", (1, ("a",), ("2", None)), id="third column title digit"),
        pytest.param("|1|a|[_]()|", (1, ("a",), ("_", None)), id="third column title underscore"),
        pytest.param("|1|a|[-]()|", (1, ("a",), ("-", None)), id="third column title dash"),
        pytest.param(
            "|1|a|[:]()|", (1, ("a",), (":", None)), id="third column title punctuation colon"
        ),
        pytest.param(
            "|1|a|[!]()|",
            (1, ("a",), ("!", None)),
            id="third column title punctuation exclamation",
        ),
        pytest.param(
            "|1|a|[+]()|", (1, ("a",), ("+", None)), id="third column title punctuation plus"
        ),
        pytest.param(
            "|1|a|[?]()|", (1, ("a",), ("?", None)), id="third column title punctuation question"
        ),
        pytest.param("|1|a|[c d]()|", (1, ("a",), ("c d", None)), id="third column title space"),
        pytest.param(
            "|1|a|[ b]()|", (1, ("a",), ("b", None)), id="third column title space before"
        ),
        pytest.param(
            "|1|a|[b ]()|", (1, ("a",), ("b", None)), id="third column title space after"
        ),
        pytest.param(
            "|1|a|[b c]()|", (1, ("a",), ("b c", None)), id="third column title embedded space"
        ),
        pytest.param("|1|a|[b](c)|", (1, ("a",), ("b", "c")), id="third column link defined"),
        pytest.param(
            "|1|a|[b] (c)|",
            (1, ("a",), ("b", "c")),
            id="third column white spave between title and link",
        ),
        pytest.param(
            "|1|a|[b]( c)|", (1, ("a",), ("b", "c")), id="third column link whitespace before"
        ),
        pytest.param(
            "|1|a|[b](c )|", (1, ("a",), ("b", "c")), id="third column link whitespace after"
        ),
        pytest.param(
            "|1|a|[b](cd)|", (1, ("a",), ("b", "cd")), id="third column link multiple characters"
        ),
        pytest.param("|1|a|[b](C)|", (1, ("a",), ("b", "C")), id="third column link upper case"),
        pytest.param("|1|a|[b](2)|", (1, ("a",), ("b", "2")), id="third column link digit"),
        pytest.param(
            "|1|a|[b](/)|", (1, ("a",), ("b", "/")), id="third column link forward slash"
        ),
        pytest.param("|1|a|[b](-)|", (1, ("a",), ("b", "-")), id="third column link dash"),
    ],
)
def test__line_to_row(line: str, expected_result: types_.TableRow):
    """
    arrange: given line and expected return value
    act: when _line_to_row is called with the line
    assert: then the expected return value is returned.
    """
    returned_result = navigation_table._line_to_row(line)

    assert returned_result == expected_result


def test__line_to_row_no_match():
    """
    arrange: given line that does not match
    act: when _line_to_row is called with the line
    assert: then NavigationTableParseError is raised.
    """
    with pytest.raises(NavigationTableParseError):
        navigation_table._line_to_row("")


def test__check_table_row_write_permission_group():
    """
    arrange: given mocked discourse and table row for a group
    act: when _check_table_row_write_permission is called with the table row and mocked discourse
    assert: then the table row is returned.
    """
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    table_row = types_.TableRow(
        level=1, path=("path 1",), navlink=types_.Navlink(title="title 1", link=None)
    )

    returned_table_row = navigation_table._check_table_row_write_permission(
        table_row=table_row, discourse=mocked_discourse
    )

    assert returned_table_row == table_row
    mocked_discourse.check_topic_write_permission.assert_not_called()


def test__check_table_row_write_permission_page_error():
    """
    arrange: given mocked discourse that raises an error and table row for a page
    act: when _check_table_row_write_permission is called with the table row and mocked discourse
    assert: then ServerError is raised.
    """
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.check_topic_write_permission.side_effect = exceptions.DiscourseError

    with pytest.raises(exceptions.ServerError) as exc_info:
        navigation_table._check_table_row_write_permission(
            table_row=types_.TableRow(
                level=1,
                path=("path 1",),
                navlink=types_.Navlink(title="title 1", link=(link := "link 1")),
            ),
            discourse=mocked_discourse,
        )

    assert link in str(exc_info.value)


def test__check_table_row_write_permission_page_false():
    """
    arrange: given mocked discourse that returns false for write permission and table row for a
        page
    act: when _check_table_row_write_permission is called with the table row and mocked discourse
    assert: then PagePermissionError is raised.
    """
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.check_topic_write_permission.return_value = False

    with pytest.raises(exceptions.PagePermissionError) as exc_info:
        navigation_table._check_table_row_write_permission(
            table_row=types_.TableRow(
                level=1,
                path=("path 1",),
                navlink=types_.Navlink(title="title 1", link=(link := "link 1")),
            ),
            discourse=mocked_discourse,
        )

    assert_substrings_in_string((link, "write", "permission"), str(exc_info.value))


def test__check_table_row_write_permission_page_true():
    """
    arrange: given mocked discourse that returns true for write permission and table row for a page
    act: when _check_table_row_write_permission is called with the table row and mocked discourse
    assert: then the table row is returned.
    """
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.check_topic_write_permission.return_value = True
    table_row = types_.TableRow(
        level=1,
        path=("path 1",),
        navlink=types_.Navlink(title="title 1", link=(link := "link 1")),
    )

    returned_table_row = navigation_table._check_table_row_write_permission(
        table_row=table_row, discourse=mocked_discourse
    )

    assert returned_table_row == table_row
    mocked_discourse.check_topic_write_permission.assert_called_once_with(url=link)


def test_from_page_missing_write_permission():
    """
    arrange: given page and mocked discourse server that returns false for the write permission
    act: when from_page is called with the page
    assert: then PagePermissionError is raised.
    """
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.check_topic_write_permission.return_value = False

    with pytest.raises(exceptions.PagePermissionError):
        list(
            navigation_table.from_page(
                page="|level|path|navlink|\n|1|a|[b](c)|", discourse=mocked_discourse
            )
        )


@pytest.mark.parametrize(
    "page, expected_table",
    [
        pytest.param("", [], id="empty"),
        pytest.param("|level|path|navlink|", [], id="header only"),
        pytest.param("|level|path|navlink|\n|-|-|-|", [], id="header, filler"),
        pytest.param(
            "|level|path|navlink|\n|-|-|-|\n|1|a|[b]()|",
            [(1, ("a",), ("b", None))],
            id="header, filler and single row",
        ),
        pytest.param(
            "|level|path|navlink|\n|1|a|[b]()|",
            [(1, ("a",), ("b", None))],
            id="header, single row",
        ),
        pytest.param(
            "text 1\n|level|path|navlink|\n|1|a|[b]()|",
            [(1, ("a",), ("b", None))],
            id="text, header, single row",
        ),
        pytest.param(
            "|level|path|navlink|\n|1|a|[b]()|\n|2|c|[d]()|",
            [
                (1, ("a",), ("b", None)),
                (
                    2,
                    (
                        "a",
                        "c",
                    ),
                    ("d", None),
                ),
            ],
            id="header, multiple rows",
        ),
    ],
)
def test_from_page(page: str, expected_table: list[types_.TableRow]):
    """
    arrange: given page and expected table
    act: when from_page is called with the page
    assert: then the expected rtable is returned.
    """
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.check_topic_write_permission.return_value = True

    returned_table = navigation_table.from_page(page=page, discourse=mocked_discourse)

    assert list(returned_table) == expected_table


def test_from_page_indico():
    """
    arrange: given Indico's navigation page
    act: when from_page is called with the page
    assert: then the page is parsed.
    """
    # Line is too long as the indico docs are not limited to 100 characters per line
    # pylint: disable=line-too-long
    indico_page = """Indico is an open-source tool for event organisation, archival and collaboration, catering to lectures, meetings, workshops and conferences.

For details on Indico's features, see [this page](https://getindico.io/features/).

# Navigation

| Level | Path | Navlink |
| -- | -- | -- |
| 1 | tutorials | [Tutorials]() |
| 1 | how-to-guides | [How-to guides]() |
| 2 | contributing | [Contributing](/t/indico-docs-contributing/6574)|
| 2 | cross-model-db-relations | [Cross-model DB relations](/t/indico-docs-cross-model-relations-for-pg/7009)|
| 2 | refresh-external-resources | [Refreshing external resources](/t/indico-docs-refreshing-external-resources/7008) |
| 1 | reference | [Reference]() |
| 2 | plugins | [Plugins](/t/indico-docs-plugins/6553) |
| 2 | theme-customisation | [Theme Customisation](/t/indico-docs-themes/6554) |
| 1 | explanation | [Explanation]() |
| 2 | charm-architecture | [Charm Architecture](/t/indico-docs-charm-architecture/7010) |"""  # noqa: E501
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.check_topic_write_permission.return_value = True

    returned_table = navigation_table.from_page(page=indico_page, discourse=mocked_discourse)

    assert list(returned_table) == [
        (1, ("tutorials",), ("Tutorials", None)),
        (1, ("how-to-guides",), ("How-to guides", None)),
        (
            2,
            ("how-to-guides", "contributing"),
            ("Contributing", "/t/indico-docs-contributing/6574"),
        ),
        (
            2,
            ("how-to-guides", "cross-model-db-relations"),
            ("Cross-model DB relations", "/t/indico-docs-cross-model-relations-for-pg/7009"),
        ),
        (
            2,
            ("how-to-guides", "refresh-external-resources"),
            ("Refreshing external resources", "/t/indico-docs-refreshing-external-resources/7008"),
        ),
        (1, ("reference",), ("Reference", None)),
        (2, ("reference", "plugins"), ("Plugins", "/t/indico-docs-plugins/6553")),
        (
            2,
            ("reference", "theme-customisation"),
            ("Theme Customisation", "/t/indico-docs-themes/6554"),
        ),
        (1, ("explanation",), ("Explanation", None)),
        (
            2,
            ("explanation", "charm-architecture"),
            ("Charm Architecture", "/t/indico-docs-charm-architecture/7010"),
        ),
    ]


def test_from_page_indico_path():
    """
    arrange: given Indico's navigation page
    act: when from_page is called with the page
    assert: then the page is parsed.
    """
    # Line is too long as the indico docs are not limited to 100 characters per line
    # pylint: disable=line-too-long
    indico_page = """Indico is an open-source tool for event organisation, archival and collaboration, catering to lectures, meetings, workshops and conferences.

For details on Indico's features, see [this page](https://getindico.io/features/).

# Navigation

| Level | Path | Navlink |
| -- | -- | -- |
| 1 | tutorials | [Tutorials]() |
| 1 | how-to-guides | [How-to guides]() |
| 2 | how-to-guides-contributing | [Contributing](/t/indico-docs-contributing/6574)|
| 2 | how-to-guides-cross-model-db-relations | [Cross-model DB relations](/t/indico-docs-cross-model-relations-for-pg/7009)|
| 2 | how-to-guides-refresh-external-resources | [Refreshing external resources](/t/indico-docs-refreshing-external-resources/7008) |
| 1 | reference | [Reference]() |
| 2 | reference-plugins | [Plugins](/t/indico-docs-plugins/6553) |
| 2 | reference-theme-customisation | [Theme Customisation](/t/indico-docs-themes/6554) |
| 1 | explanation | [Explanation]() |
| 2 | explanation-charm-architecture | [Charm Architecture](/t/indico-docs-charm-architecture/7010) |"""  # noqa: E501
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.check_topic_write_permission.return_value = True

    returned_table = navigation_table.from_page(page=indico_page, discourse=mocked_discourse)

    assert list(returned_table) == [
        (1, ("tutorials",), ("Tutorials", None)),
        (1, ("how-to-guides",), ("How-to guides", None)),
        (
            2,
            ("how-to-guides", "contributing"),
            ("Contributing", "/t/indico-docs-contributing/6574"),
        ),
        (
            2,
            ("how-to-guides", "cross-model-db-relations"),
            ("Cross-model DB relations", "/t/indico-docs-cross-model-relations-for-pg/7009"),
        ),
        (
            2,
            ("how-to-guides", "refresh-external-resources"),
            ("Refreshing external resources", "/t/indico-docs-refreshing-external-resources/7008"),
        ),
        (1, ("reference",), ("Reference", None)),
        (2, ("reference", "plugins"), ("Plugins", "/t/indico-docs-plugins/6553")),
        (
            2,
            ("reference", "theme-customisation"),
            ("Theme Customisation", "/t/indico-docs-themes/6554"),
        ),
        (1, ("explanation",), ("Explanation", None)),
        (
            2,
            ("explanation", "charm-architecture"),
            ("Charm Architecture", "/t/indico-docs-charm-architecture/7010"),
        ),
    ]
