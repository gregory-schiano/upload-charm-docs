# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for run module."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from pathlib import Path
from unittest import mock

import pytest

from src import discourse, index, types_
from src.exceptions import DiscourseError, ServerError

from .. import factories
from .helpers import assert_substrings_in_string


def test__read_docs_index_docs_directory_missing(tmp_path: Path):
    """
    arrange: given empty directory
    act: when _read_docs_index is called with the directory
    assert: then None is returned.
    """
    returned_content = index._read_docs_index(base_path=tmp_path)

    assert returned_content is None


def test__read_docs_index_index_file_missing(tmp_path: Path):
    """
    arrange: given directory with the docs folder
    act: when _read_docs_index is called with the directory
    assert: then None is returned.
    """
    docs_directory = tmp_path / index.DOCUMENTATION_FOLDER_NAME
    docs_directory.mkdir()

    returned_content = index._read_docs_index(base_path=tmp_path)

    assert returned_content is None


def test__read_docs_index_index_file(index_file_content: str, tmp_path: Path):
    """
    arrange: given directory with the docs folder and index file
    act: when _read_docs_index is called with the directory
    assert: then the index file content is returned.
    """
    returned_content = index._read_docs_index(base_path=tmp_path)

    assert returned_content == index_file_content


def test_get_metadata_yaml_retrieve_discourse_error(tmp_path: Path):
    """
    arrange: given directory with metadata.yaml with docs defined and discourse client that
        raises DiscourseError
    act: when get is called with that directory
    assert: then ServerError is raised.
    """
    meta = types_.Metadata(name="name", docs="http://server/index-page")
    mocked_server_client = mock.MagicMock(spec=discourse.Discourse)
    mocked_server_client.retrieve_topic.side_effect = DiscourseError

    with pytest.raises(ServerError) as exc_info:
        index.get(metadata=meta, base_path=tmp_path, server_client=mocked_server_client)

    assert_substrings_in_string(("index page", "retrieval", "failed"), str(exc_info.value).lower())


def test_get_metadata_yaml_retrieve_local_and_server(tmp_path: Path, index_file_content: str):
    """
    arrange: given directory with metadata.yaml with docs defined and discourse client that
        returns the index page content and local index file
    act: when get is called with that directory
    assert: then retrieve topic is called with the docs key value and the content returned by the
        client, docs key and local file information is returned.
    """
    url = "http://server/index-page"
    name = "name 1"
    meta = types_.Metadata(name=name, docs=url)
    mocked_server_client = mock.MagicMock(spec=discourse.Discourse)
    mocked_server_client.retrieve_topic.return_value = (content := "content 2")

    returned_index = index.get(
        metadata=meta, base_path=tmp_path, server_client=mocked_server_client
    )

    assert returned_index.server is not None
    assert returned_index.server.url == url
    assert returned_index.server.content == content
    assert returned_index.local.title == "Name 1 Documentation Overview"
    assert returned_index.local.content == index_file_content
    assert returned_index.name == name
    mocked_server_client.retrieve_topic.assert_called_once_with(url=url)


def test_get_metadata_yaml_retrieve_empty(tmp_path: Path):
    """
    arrange: given directory with metadata.yaml without docs defined and empty local documentation
    act: when get is called with that directory
    assert: then all information is None except the title.
    """
    name = "name 1"
    meta = types_.Metadata(name=name, docs=None)
    mocked_server_client = mock.MagicMock(spec=discourse.Discourse)

    returned_index = index.get(
        metadata=meta, base_path=tmp_path, server_client=mocked_server_client
    )

    assert returned_index.server is None
    assert returned_index.local.title == "Name 1 Documentation Overview"
    assert returned_index.local.content is None
    assert returned_index.name == name


# Pylint doesn't understand how the walrus operator works
# pylint: disable=undefined-variable,unused-variable
@pytest.mark.parametrize(
    "page, expected_content",
    [
        pytest.param(
            index.NAVIGATION_TABLE_START,
            "",
            id="navigation table only",
        ),
        pytest.param(
            (content := "Page content"),
            content,
            id="page content only",
        ),
        pytest.param(
            (multiline_content := "Page content\nWithMultiline"),
            multiline_content,
            id="multiline content only",
        ),
        pytest.param(
            f"{(content := 'Page content')}{index.NAVIGATION_TABLE_START}",
            content,
            id="page with content and navigation table",
        ),
        pytest.param(
            f"{(content := 'page content')}{index.NAVIGATION_TABLE_START}\ncontent-afterwards",
            content,
            id="page with content after the navigation table",
        ),
    ],
)
# pylint: enable=undefined-variable,unused-variable
def test_get_contents_from_page(page: str, expected_content: str):
    """
    arrange: given an index page from server
    act: when contents_from_page is called
    assert: contents without navigation table is returned.
    """
    assert index.contents_from_page(page=page) == expected_content


# Trying something new which may be worthwhile to roll out to the rest of the repo to limit the
# scope of variables in the parametrized tests


def _test__get_contents_list_items_parameters():
    """Generate parameters for the test__get_contents_list_items test."""
    return [
        pytest.param(
            None,
            (),
            id="missing file",
        ),
        pytest.param(
            "",
            (),
            id="empty file",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})""",
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_1, reference_value=value_1, rank=1
                )
            ),
            id="single item",
        ),
        pytest.param(
            f"""# Contents
1. [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})""",
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_1, reference_value=value_1, rank=1
                )
            ),
            id="single item numbered",
        ),
        pytest.param(
            f"""# Contents
* [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})""",
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_1, reference_value=value_1, rank=1
                )
            ),
            id="single item star",
        ),
        pytest.param(
            f"""# Other content
- [other title 1](other value 1)

# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})""",
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_1, reference_value=value_1, rank=1
                )
            ),
            id="single item content before",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})

# Other content
- [other title 1](other value 1)
""",
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_1, reference_value=value_1, rank=1
                )
            ),
            id="single item content after",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})

# Contents
- [other title 1](other value 1)
""",
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_1, reference_value=value_1, rank=1
                )
            ),
            id="single item content after with duplicate heading",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
- [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
""",
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_1, reference_value=value_1, rank=1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_2, reference_value=value_2, rank=2
                ),
            ),
            id="multiple items flat",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
  - [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
""",
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_1, reference_value=value_1, rank=1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_2, reference_value=value_2, rank=2
                ),
            ),
            id="multiple items nested",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
  1. [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
""",
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_1, reference_value=value_1, rank=1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_2, reference_value=value_2, rank=2
                ),
            ),
            id="multiple items nested alternate leader",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
- [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
- [{(title_3 := 'title 3')}]({(value_3 := 'value 3')})
""",
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_1, reference_value=value_1, rank=1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_2, reference_value=value_2, rank=2
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_3, reference_value=value_3, rank=3
                ),
            ),
            id="many items flat",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
  - [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
- [{(title_3 := 'title 3')}]({(value_3 := 'value 3')})
""",
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_1, reference_value=value_1, rank=1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_2, reference_value=value_2, rank=2
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_3, reference_value=value_3, rank=3
                ),
            ),
            id="many items second nested",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
- [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
  - [{(title_3 := 'title 3')}]({(value_3 := 'value 3')})
""",
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_1, reference_value=value_1, rank=1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_2, reference_value=value_2, rank=2
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_3, reference_value=value_3, rank=3
                ),
            ),
            id="many items last nested",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
  - [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
  - [{(title_3 := 'title 3')}]({(value_3 := 'value 3')})
""",
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_1, reference_value=value_1, rank=1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_2, reference_value=value_2, rank=2
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_3, reference_value=value_3, rank=3
                ),
            ),
            id="many items nested",
        ),
        pytest.param(
            f"""# Contents
- [{(title_1 := 'title 1')}]({(value_1 := 'value 1')})
  - [{(title_2 := 'title 2')}]({(value_2 := 'value 2')})
    - [{(title_3 := 'title 3')}]({(value_3 := 'value 3')})
""",
            (
                factories.IndexContentsListItemFactory(
                    hierarchy=0, reference_title=title_1, reference_value=value_1, rank=1
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=1, reference_title=title_2, reference_value=value_2, rank=2
                ),
                factories.IndexContentsListItemFactory(
                    hierarchy=2, reference_title=title_3, reference_value=value_3, rank=3
                ),
            ),
            id="many items deeply nested",
        ),
    ]


@pytest.mark.parametrize("content, expected_items", _test__get_contents_list_items_parameters())
def test__get_contents_list_items(
    content: str, expected_items: tuple[types_.IndexContentsListItem, ...]
):
    """
    arrange: given the index file contents
    act: when get_contents_list_items is called with the index file
    assert: then the expected contents list items are returned.
    """
    index_file = types_.IndexFile(title="title 1", content=content)

    returned_items = tuple(index._get_contents_list_items(index_file=index_file))

    assert returned_items == expected_items
