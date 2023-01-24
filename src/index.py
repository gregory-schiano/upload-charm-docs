# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Execute the uploading of documentation."""

import itertools
import re
import typing
from pathlib import Path

from .discourse import Discourse
from .exceptions import DiscourseError, InputError, ServerError
from .reconcile import NAVIGATION_TABLE_START
from .types_ import Index, IndexContentsListItem, IndexFile, Metadata, Page

DOCUMENTATION_FOLDER_NAME = "docs"
DOCUMENTATION_INDEX_FILENAME = "index.md"

_WHITESPACE = "( *)"
_LEADER = r"((\d\.)|(\*)|(-))"
_REFERENCE_TITLE = r"\[(.*)\]"
_REFERENCE_VALUE = r"\((.*)\)"
_REFERENCE = rf"({_REFERENCE_TITLE}{_REFERENCE_VALUE})"
_ITEM = rf"^{_WHITESPACE}{_LEADER}\s*{_REFERENCE}\s*$"
_ITEM_PATTERN = re.compile(_ITEM)


def _read_docs_index(base_path: Path) -> str | None:
    """Read the content of the index file.

    Args:
        base_path: The starting path to look for the index content.

    Returns:
        The content of the index file if it exists, otherwise return None.

    """
    if not (docs_directory := base_path / DOCUMENTATION_FOLDER_NAME).is_dir():
        return None
    if not (index_file := docs_directory / DOCUMENTATION_INDEX_FILENAME).is_file():
        return None

    return index_file.read_text()


def get(metadata: Metadata, base_path: Path, server_client: Discourse) -> Index:
    """Retrieve the local and server index information.

    Args:
        metadata: Information about the charm.
        base_path: The base path to look for the metadata file in.
        server_client: A client to the documentation server.

    Returns:
        The index page.

    Raises:
        ServerError: if interactions with the documentation server occurs.

    """
    if metadata.docs is not None:
        index_url = metadata.docs
        try:
            server_content = server_client.retrieve_topic(url=index_url)
        except DiscourseError as exc:
            raise ServerError("Index page retrieval failed") from exc
        server = Page(url=index_url, content=server_content)
    else:
        server = None

    name_value = metadata.name
    local_content = _read_docs_index(base_path=base_path)
    local = IndexFile(
        title=f"{name_value.replace('-', ' ').title()} Documentation Overview",
        content=local_content,
    )

    return Index(server=server, local=local, name=name_value)


def contents_from_page(page: str) -> str:
    """Get index file contents from server page.

    Args:
        page: Page contents from server.

    Returns:
        Index file contents.
    """
    contents = page.split(NAVIGATION_TABLE_START)
    return contents[0]


class _ParsedListItem(typing.NamedTuple):
    """Represents a parsed item in the contents table.

    Attrs:
        whitespace_count: The number of leading whitespace characters
        reference_title: The name of the reference
        reference_value: The link to the referenced item
        rank: The number of preceding elements in the list
    """

    whitespace_count: int
    reference_title: str
    reference_value: str
    rank: int


def _parse_item_from_line(line: str, rank: int) -> _ParsedListItem:
    """Parse an index list item from a contents line.

    Args:
        line: The contents line to parse.

    Returns:
        The parsed content item.
    """
    match = _ITEM_PATTERN.match(line)

    if match is None:
        raise InputError(
            f"An item in the contents of the index file at {DOCUMENTATION_INDEX_FILENAME} is "
            f"invalid, {line=!r}, expecting regex: {_ITEM}"
        )

    whitespace_count = len(match.group(1))

    if whitespace_count != 0 and rank == 0:
        raise InputError(
            f"An item in the contents of the index file at {DOCUMENTATION_INDEX_FILENAME} is "
            f"invalid, {line=!r}, expecting the first line not to have any leading whitespace"
        )

    reference_title = match.group(7)
    reference_value = match.group(8)

    return _ParsedListItem(
        whitespace_count=whitespace_count,
        reference_title=reference_title,
        reference_value=reference_value,
        rank=rank,
    )


def _get_contents_parsed_list_items(index_file: IndexFile) -> typing.Iterator[_ParsedListItem]:
    """Get the items from the contents list of the index file.

    Args:
        index_file: The index file to read the contents from.

    Yields:
        All the items on the contents list in the index file.
    """
    if index_file.content is None:
        return

    # Get the lines of the contents section
    lines = index_file.content.splitlines()
    # Advance past the contents heading
    lines_from_contents = itertools.dropwhile(lambda line: line.lower() != "# contents", lines)
    next(lines_from_contents, None)
    # Stop taking on the next heading
    contents_lines = itertools.takewhile(
        lambda line: not line.startswith("#"), lines_from_contents
    )
    # Remove empty lines
    contents_lines = filter(None, contents_lines)

    yield from map(
        lambda line_rank: _parse_item_from_line(*line_rank), zip(contents_lines, itertools.count())
    )
