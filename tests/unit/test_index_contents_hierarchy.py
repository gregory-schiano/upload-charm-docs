# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for run module."""

# Need access to protected functions for testing
# pylint: disable=protected-access

import typing
from pathlib import Path

import pytest
from more_itertools import peekable

from src import constants, docs_directory, exceptions, index, types_

from .. import factories
from .helpers import assert_substrings_in_string, create_dir, create_file


def _test__calculate_contents_hierarchy_invalid_parameters():
    """Generate parameters for the test__calculate_contents_hierarchy_invalid test.

    Returns:
        The tests.
    """
    return [
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value="file_1.md",
                    rank=1,
                ),
            ),
            (),
            ("not", "file or directory", repr(item)),
            id="file doesn't exist",
        ),
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value="file_1.txt",
                    rank=1,
                ),
            ),
            (create_file,),
            ("not", "expected", "file type", constants.DOC_FILE_EXTENSION, repr(item)),
            id="file wrong extension",
        ),
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 1",
                    reference_value="file_1.md",
                    rank=1,
                ),
            ),
            (create_file,),
            ("more", "whitespace", "0", repr(item)),
            id="file wrong whitespace",
        ),
        pytest.param(
            (
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 1",
                    reference_value="dir_1",
                    rank=1,
                ),
            ),
            (create_dir,),
            ("more", "whitespace", "0", repr(item)),
            id="directory wrong whitespace",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value="file_1.md",
                    rank=1,
                ),
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 2",
                    reference_value="file_2.md",
                    rank=2,
                ),
            ),
            (create_file, create_file),
            ("more", "whitespace", "0", repr(item)),
            id="file wrong nesting",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value=(expected_dir := "dir_1"),
                    rank=1,
                ),
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 2",
                    reference_value="file_2.md",
                    rank=2,
                ),
            ),
            (create_dir, create_file),
            ("not within", "directory", expected_dir, repr(item)),
            id="file wrong directory",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value=(expected_dir := "dir_1"),
                    rank=1,
                ),
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 2",
                    reference_value="dir_2",
                    rank=2,
                ),
            ),
            (create_dir, create_dir),
            ("not within", "directory", expected_dir, repr(item)),
            id="directory wrong directory",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value=(value_1 := "dir_1"),
                    rank=1,
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 2",
                    reference_value=(value_2 := f"{value_1}/dir_2"),
                    rank=2,
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 3",
                    reference_value=f"{value_1}/file_3.md",
                    rank=3,
                ),
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 4",
                    reference_value=f"{value_2}/file_4.md",
                    rank=4,
                ),
            ),
            (create_dir, create_dir, create_file, create_file),
            ("not immediately within", "directory", value_1, repr(item)),
            id="file in wrong directory",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title="title 1",
                    reference_value=(value_1 := "dir_1"),
                    rank=1,
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 2",
                    reference_value=(value_2 := f"{value_1}/dir_2"),
                    rank=2,
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 3",
                    reference_value=f"{value_1}/file_3.md",
                    rank=3,
                ),
                item := factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title="title 4",
                    reference_value=f"{value_2}/dir_4",
                    rank=4,
                ),
            ),
            (create_dir, create_dir, create_file, create_dir),
            ("not immediately within", "directory", value_1, repr(item)),
            id="directory in wrong directory",
        ),
    ]


@pytest.mark.parametrize(
    "parsed_items, create_path_funcs, expected_contents",
    _test__calculate_contents_hierarchy_invalid_parameters(),
)
def test__calculate_contents_hierarchy_invalid(
    parsed_items: tuple[index._ParsedListItem, ...],
    create_path_funcs: tuple[typing.Callable[[str, Path], None], ...],
    expected_contents: tuple[str, ...],
    tmp_path: Path,
):
    """
    arrange: given the index file contents
    act: when get_contents_list_items is called with the index file
    assert: then the expected contents list items are returned.
    """
    # Create the paths
    for parsed_item, create_path_func in zip(parsed_items, create_path_funcs):
        create_path_func(parsed_item.reference_value, tmp_path)

    with pytest.raises(exceptions.InputError) as exc_info:
        tuple(
            index._calculate_contents_hierarchy(
                parsed_items=peekable(parsed_items), base_dir=tmp_path
            )
        )

    assert_substrings_in_string(expected_contents, str(exc_info.value))


def _test__calculate_contents_hierarchy_parameters():
    """Generate parameters for the test__calculate_contents_hierarchy test.

    Returns:
        The tests.
    """
    return [
        pytest.param((), (), (), id="empty"),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title := "title 1"),
                    reference_value=(value := "file_1.md"),
                    rank=(rank := 1),
                ),
            ),
            (create_file,),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title, reference_value=value, rank=rank
                ),
            ),
            id="single file",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title := "title 1"),
                    reference_value=(value := "file_1.MD"),
                    rank=(rank := 1),
                ),
            ),
            (create_file,),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title, reference_value=value, rank=rank
                ),
            ),
            id="single file upper case extension",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title := "title 1"),
                    reference_value=(value := "dir_1"),
                    rank=(rank := 1),
                ),
            ),
            (create_dir,),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title, reference_value=value, rank=rank
                ),
            ),
            id="single directory",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_1 := "title 1"),
                    reference_value=(value_1 := "file_1.md"),
                    rank=(rank_1 := 1),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_2 := "title 2"),
                    reference_value=(value_2 := "file_2.md"),
                    rank=(rank_2 := 2),
                ),
            ),
            (create_file, create_file),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=rank_1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_2, reference_value=value_2, rank=rank_2
                ),
            ),
            id="multiple files",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_1 := "title 1"),
                    reference_value=(value_1 := "dir_1"),
                    rank=(rank_1 := 1),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_2 := "title 2"),
                    reference_value=(value_2 := "dir_2"),
                    rank=(rank_2 := 2),
                ),
            ),
            (create_dir, create_dir),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=rank_1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_2, reference_value=value_2, rank=rank_2
                ),
            ),
            id="multiple directories",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_1 := "title 1"),
                    reference_value=(value_1 := "file_1.md"),
                    rank=(rank_1 := 1),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_2 := "title 2"),
                    reference_value=(value_2 := "dir_2"),
                    rank=(rank_2 := 2),
                ),
            ),
            (create_file, create_dir),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=rank_1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_2, reference_value=value_2, rank=rank_2
                ),
            ),
            id="single file single directory",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_1 := "title 1"),
                    reference_value=(value_1 := "dir_1"),
                    rank=(rank_1 := 1),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_2 := "title 2"),
                    reference_value=(value_2 := "file_2.md"),
                    rank=(rank_2 := 2),
                ),
            ),
            (create_dir, create_file),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=rank_1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_2, reference_value=value_2, rank=rank_2
                ),
            ),
            id="single directory single file",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_1 := "title 1"),
                    reference_value=(value_1 := "dir_1"),
                    rank=(rank_1 := 1),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title=(title_2 := "title 2"),
                    reference_value=(value_2 := f"{value_1}/file_2.md"),
                    rank=(rank_2 := 2),
                ),
            ),
            (create_dir, create_file),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=rank_1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2, reference_title=title_2, reference_value=value_2, rank=rank_2
                ),
            ),
            id="single directory single file in directory",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_1 := "title 1"),
                    reference_value=(value_1 := "dir_1"),
                    rank=(rank_1 := 1),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=2,
                    reference_title=(title_2 := "title 2"),
                    reference_value=(value_2 := f"{value_1}/file_2.md"),
                    rank=(rank_2 := 2),
                ),
            ),
            (create_dir, create_file),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=rank_1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2, reference_title=title_2, reference_value=value_2, rank=rank_2
                ),
            ),
            id="single directory single file in directory larger whitespace",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_1 := "title 1"),
                    reference_value=(value_1 := "dir_1"),
                    rank=(rank_1 := 1),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title=(title_2 := "title 2"),
                    reference_value=(value_2 := f"{value_1}/dir_2"),
                    rank=(rank_2 := 2),
                ),
            ),
            (create_dir, create_dir),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=rank_1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2, reference_title=title_2, reference_value=value_2, rank=rank_2
                ),
            ),
            id="single directory single directory in directory",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_1 := "title 1"),
                    reference_value=(value_1 := "file_1.md"),
                    rank=(rank_1 := 1),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_2 := "title 2"),
                    reference_value=(value_2 := "file_2.md"),
                    rank=(rank_2 := 2),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_3 := "title 3"),
                    reference_value=(value_3 := "file_3.md"),
                    rank=(rank_3 := 3),
                ),
            ),
            (create_file, create_file, create_file),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=rank_1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_2, reference_value=value_2, rank=rank_2
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_3, reference_value=value_3, rank=rank_3
                ),
            ),
            id="many files",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_1 := "title 1"),
                    reference_value=(value_1 := "dir_1"),
                    rank=(rank_1 := 1),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_2 := "title 2"),
                    reference_value=(value_2 := "dir_2"),
                    rank=(rank_2 := 2),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_3 := "title 3"),
                    reference_value=(value_3 := "dir_3"),
                    rank=(rank_3 := 3),
                ),
            ),
            (create_dir, create_dir, create_dir),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=rank_1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_2, reference_value=value_2, rank=rank_2
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_3, reference_value=value_3, rank=rank_3
                ),
            ),
            id="many directories",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_1 := "title 1"),
                    reference_value=(value_1 := "dir_1"),
                    rank=(rank_1 := 1),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title=(title_2 := "title 2"),
                    reference_value=(value_2 := f"{value_1}/file_2.md"),
                    rank=(rank_2 := 2),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_3 := "title 3"),
                    reference_value=(value_3 := "file_3.md"),
                    rank=(rank_3 := 3),
                ),
            ),
            (create_dir, create_file, create_file),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=rank_1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2, reference_title=title_2, reference_value=value_2, rank=rank_2
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_3, reference_value=value_3, rank=rank_3
                ),
            ),
            id="single file in directory",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_1 := "title 1"),
                    reference_value=(value_1 := "dir_1"),
                    rank=(rank_1 := 1),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title=(title_2 := "title 2"),
                    reference_value=(value_2 := f"{value_1}/file_2.md"),
                    rank=(rank_2 := 2),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title=(title_3 := "title 3"),
                    reference_value=(value_3 := f"{value_1}/file_3.md"),
                    rank=(rank_3 := 3),
                ),
            ),
            (create_dir, create_file, create_file),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=rank_1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2, reference_title=title_2, reference_value=value_2, rank=rank_2
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2, reference_title=title_3, reference_value=value_3, rank=rank_3
                ),
            ),
            id="multiple files in directory",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_1 := "title 1"),
                    reference_value=(value_1 := "dir_1"),
                    rank=(rank_1 := 1),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title=(title_2 := "title 2"),
                    reference_value=(value_2 := f"{value_1}/dir_2"),
                    rank=(rank_2 := 2),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=2,
                    reference_title=(title_3 := "title 3"),
                    reference_value=(value_3 := f"{value_2}/file_3.md"),
                    rank=(rank_3 := 3),
                ),
            ),
            (create_dir, create_dir, create_file),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=rank_1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2, reference_title=title_2, reference_value=value_2, rank=rank_2
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=3, reference_title=title_3, reference_value=value_3, rank=rank_3
                ),
            ),
            id="single directory single nested directory single file in nested directory",
        ),
        pytest.param(
            (
                factories.IndexParsedListItemFactory(
                    whitespace_count=0,
                    reference_title=(title_1 := "title 1"),
                    reference_value=(value_1 := "dir_1"),
                    rank=(rank_1 := 1),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=1,
                    reference_title=(title_2 := "title 2"),
                    reference_value=(value_2 := f"{value_1}/dir_2"),
                    rank=(rank_2 := 2),
                ),
                factories.IndexParsedListItemFactory(
                    whitespace_count=2,
                    reference_title=(title_3 := "title 3"),
                    reference_value=(value_3 := f"{value_2}/dir_3"),
                    rank=(rank_3 := 3),
                ),
            ),
            (create_dir, create_dir, create_dir),
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_1, reference_value=value_1, rank=rank_1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2, reference_title=title_2, reference_value=value_2, rank=rank_2
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=3, reference_title=title_3, reference_value=value_3, rank=rank_3
                ),
            ),
            id="single directory single nested directory single directory in nested directory",
        ),
    ]


@pytest.mark.parametrize(
    "parsed_items, create_path_funcs, expected_items",
    _test__calculate_contents_hierarchy_parameters(),
)
def test__calculate_contents_hierarchy(
    parsed_items: tuple[index._ParsedListItem, ...],
    create_path_funcs: tuple[typing.Callable[[str, Path], None], ...],
    expected_items: tuple[types_.IndexContentsListItem, ...],
    tmp_path: Path,
):
    """
    arrange: given the index file contents
    act: when get_contents_list_items is called with the index file
    assert: then the expected contents list items are returned.
    """
    # Create the paths
    for parsed_item, create_path_func in zip(parsed_items, create_path_funcs):
        create_path_func(parsed_item.reference_value, tmp_path)

    returned_items = tuple(
        index._calculate_contents_hierarchy(parsed_items=peekable(parsed_items), base_dir=tmp_path)
    )

    assert returned_items == expected_items