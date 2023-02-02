# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for sort module."""

# Need access to protected functions for testing
# pylint: disable=protected-access

import typing
from pathlib import Path

import pytest

from src import sort, types_

from .. import factories
from .helpers import create_dir, create_file


def change_path_info_attrs(path_info: types_.PathInfo, **kwargs: typing.Any) -> types_.PathInfo:
    """Change an attribute of a PathInfo to an alternate value.

    Args:
        path_info: The path info to change the attributes of.
        kwargs: The attributes to change with their value.

    Returns:
        The changed PathInfo.
    """
    return types_.PathInfo(**{**path_info._asdict(), **kwargs})


def _test_using_contents_index_parameters():
    """Generate parameters for the test_using_contents_index test.

    Returns:
        The tests.
    """
    return [
        pytest.param((), (), (), (), id="empty"),
        pytest.param(
            (path_info := factories.PathInfoFactory(local_path="file_1.md"),),
            (),
            (create_file,),
            (path_info,),
            id="single path info file no contents index",
        ),
        pytest.param(
            (path_info := factories.PathInfoFactory(local_path="dir_1"),),
            (),
            (create_dir,),
            (path_info,),
            id="single path info directory no contents index",
        ),
        pytest.param(
            (path_info := factories.PathInfoFactory(local_path=(path_1 := "file_1.md")),),
            (item := factories.IndexContentsListItemFactory(reference_value=path_1, hierarchy=1),),
            (create_file,),
            (change_path_info_attrs(path_info=path_info, navlink_title=item.reference_title),),
            id="single path info file matching contents index",
        ),
        pytest.param(
            (path_info := factories.PathInfoFactory(local_path=(path_1 := "dir_1")),),
            (item := factories.IndexContentsListItemFactory(reference_value=path_1, hierarchy=1),),
            (create_dir,),
            (change_path_info_attrs(path_info=path_info, navlink_title=item.reference_title),),
            id="single path info directory matching contents index",
        ),
        pytest.param(
            (
                path_info_1 := factories.PathInfoFactory(
                    local_path="file_1.md", alphabetical_rank=1
                ),
                path_info_2 := factories.PathInfoFactory(
                    local_path="file_2.md", alphabetical_rank=0
                ),
            ),
            (),
            (create_file, create_file),
            (path_info_2, path_info_1),
            id="multiple path info wrong order no contents index",
        ),
        pytest.param(
            (
                path_info_1 := factories.PathInfoFactory(local_path=(path_1 := "file_1.md")),
                path_info_2 := factories.PathInfoFactory(local_path=(path_2 := "file_2.md")),
            ),
            (
                item_1 := factories.IndexContentsListItemFactory(
                    reference_value=path_1, hierarchy=1, rank=1
                ),
                item_2 := factories.IndexContentsListItemFactory(
                    reference_value=path_2, hierarchy=1, rank=0
                ),
            ),
            (create_file, create_file),
            (
                change_path_info_attrs(
                    path_info=path_info_2, navlink_title=item_2.reference_title
                ),
                change_path_info_attrs(
                    path_info=path_info_1, navlink_title=item_1.reference_title
                ),
            ),
            id="multiple path info contents index wrong order",
        ),
        pytest.param(
            (
                path_info_1 := factories.PathInfoFactory(local_path=(path_1 := "file_1.md")),
                path_info_2 := factories.PathInfoFactory(local_path=(path_2 := "file_2.md")),
            ),
            (
                item_1 := factories.IndexContentsListItemFactory(
                    reference_value=path_1, hierarchy=1
                ),
            ),
            (create_file, create_file),
            (
                change_path_info_attrs(
                    path_info=path_info_1, navlink_title=item_1.reference_title
                ),
                path_info_2,
            ),
            id="multiple path info contents index first",
        ),
        pytest.param(
            (
                path_info_1 := factories.PathInfoFactory(local_path=(path_1 := "file_1.md")),
                path_info_2 := factories.PathInfoFactory(local_path=(path_2 := "file_2.md")),
            ),
            (
                item_2 := factories.IndexContentsListItemFactory(
                    reference_value=path_2, hierarchy=1
                ),
            ),
            (create_file, create_file),
            (
                change_path_info_attrs(
                    path_info=path_info_2, navlink_title=item_2.reference_title
                ),
                path_info_1,
            ),
            id="multiple path info contents index second",
        ),
        pytest.param(
            (
                path_info_1 := factories.PathInfoFactory(local_path=(path_1 := "file_1.md")),
                path_info_2 := factories.PathInfoFactory(local_path=(path_2 := "file_2.md")),
            ),
            (
                item_1 := factories.IndexContentsListItemFactory(
                    reference_value=path_1, hierarchy=1
                ),
                item_2 := factories.IndexContentsListItemFactory(
                    reference_value=path_2, hierarchy=1
                ),
            ),
            (create_file, create_file),
            (
                change_path_info_attrs(
                    path_info=path_info_1, navlink_title=item_1.reference_title
                ),
                change_path_info_attrs(
                    path_info=path_info_2, navlink_title=item_2.reference_title
                ),
            ),
            id="multiple path info file contents index",
        ),
        pytest.param(
            (
                path_info_1 := factories.PathInfoFactory(local_path=(path_1 := "dir_1")),
                path_info_2 := factories.PathInfoFactory(local_path=(path_2 := "dir_2")),
            ),
            (
                item_1 := factories.IndexContentsListItemFactory(
                    reference_value=path_1, hierarchy=1
                ),
                item_2 := factories.IndexContentsListItemFactory(
                    reference_value=path_2, hierarchy=1
                ),
            ),
            (create_dir, create_dir),
            (
                change_path_info_attrs(
                    path_info=path_info_1, navlink_title=item_1.reference_title
                ),
                change_path_info_attrs(
                    path_info=path_info_2, navlink_title=item_2.reference_title
                ),
            ),
            id="multiple path info directory contents index",
        ),
        pytest.param(
            (
                path_info_1 := factories.PathInfoFactory(local_path=(path_1 := "file_1.md")),
                path_info_2 := factories.PathInfoFactory(local_path=(path_2 := "dir_2")),
            ),
            (
                item_1 := factories.IndexContentsListItemFactory(
                    reference_value=path_1, hierarchy=1
                ),
                item_2 := factories.IndexContentsListItemFactory(
                    reference_value=path_2, hierarchy=1
                ),
            ),
            (create_file, create_dir),
            (
                change_path_info_attrs(
                    path_info=path_info_1, navlink_title=item_1.reference_title
                ),
                change_path_info_attrs(
                    path_info=path_info_2, navlink_title=item_2.reference_title
                ),
            ),
            id="multiple path info file and directory contents index",
        ),
        pytest.param(
            (
                path_info_2 := factories.PathInfoFactory(local_path=(path_2 := "dir_1")),
                path_info_1 := factories.PathInfoFactory(
                    local_path=(path_1 := f"{path_2}/file_2.md")
                ),
            ),
            (
                item_1 := factories.IndexContentsListItemFactory(
                    reference_value=path_1, hierarchy=1
                ),
                item_2 := factories.IndexContentsListItemFactory(
                    reference_value=path_2, hierarchy=2
                ),
            ),
            (create_dir, create_file),
            (
                change_path_info_attrs(
                    path_info=path_info_1, navlink_title=item_1.reference_title
                ),
                change_path_info_attrs(
                    path_info=path_info_2, navlink_title=item_2.reference_title
                ),
            ),
            id="multiple path info file in directory contents index",
        ),
        pytest.param(
            (
                path_info_2 := factories.PathInfoFactory(local_path=(path_2 := "dir_1")),
                path_info_1 := factories.PathInfoFactory(local_path=(path_1 := f"{path_2}/dir_2")),
            ),
            (
                item_1 := factories.IndexContentsListItemFactory(
                    reference_value=path_1, hierarchy=1
                ),
                item_2 := factories.IndexContentsListItemFactory(
                    reference_value=path_2, hierarchy=2
                ),
            ),
            (create_dir, create_dir),
            (
                change_path_info_attrs(
                    path_info=path_info_1, navlink_title=item_1.reference_title
                ),
                change_path_info_attrs(
                    path_info=path_info_2, navlink_title=item_2.reference_title
                ),
            ),
            id="multiple path info directory in directory contents index",
        ),
    ]


@pytest.mark.parametrize(
    "path_infos, index_contents, create_path_funcs, expected_path_infos",
    _test_using_contents_index_parameters(),
)
def test_using_contents_index(
    path_infos: tuple[types_.PathInfo, ...],
    index_contents: tuple[types_.IndexContentsListItem, ...],
    create_path_funcs: tuple[typing.Callable[[str, Path], None], ...],
    expected_path_infos: tuple[types_.PathInfo, ...],
    tmp_path: Path,
):
    """
    arrange: given path infos and index file contents
    act: when using_contents_index is called with the path infos and index contents
    assert: then the expected path infos are returned.
    """
    # Create the paths
    for path_info, create_path_func in zip(path_infos, create_path_funcs):
        create_path_func(str(path_info.local_path), tmp_path)
    # Change path infos and expected path infos to have absolute paths which is the expectation
    path_infos = tuple(
        change_path_info_attrs(path_info=path_info, local_path=tmp_path / path_info.local_path)
        for path_info in path_infos
    )
    expected_path_infos = tuple(
        change_path_info_attrs(path_info=path_info, local_path=tmp_path / path_info.local_path)
        for path_info in expected_path_infos
    )

    returned_path_infos = tuple(
        sort.using_contents_index(
            path_infos=path_infos, index_contents=index_contents, base_dir=tmp_path
        )
    )

    assert returned_path_infos == expected_path_infos
