# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Sort items for publishing."""

import itertools
import typing
from pathlib import Path

from more_itertools import peekable, side_effect

from . import types_


def using_contents_index(
    path_infos: typing.Iterable[types_.PathInfo],
    index_contents: typing.Iterable[types_.IndexContentsListItem],
    base_dir: Path,
) -> typing.Iterator[types_.PathInfo]:
    """Sort PathInfos based on the contents index and alphabetical rank.

    Also updates the navlink title for any items matched to the contents index.

    Args:
        path_infos: Information about the local documentation files.
        index_contents: The content index items used to apply sorting.
        base_dir: The directory the documentation files are contained within.

    Yields:
        PathInfo sorted based on their location on the contents index and then by alphabetical
        rank.
    """
    # Ensure initial sorting is correct
    alphabetically_sorted_path_infos = sorted(
        path_infos, key=lambda path_info: path_info.alphabetical_rank
    )
    rank_sorted_index_contents = sorted(index_contents, key=lambda item: item.rank)

    # Data structures required for sorting
    local_path_yielded = {
        path_info.local_path: False for path_info in alphabetically_sorted_path_infos
    }
    local_path_path_info = {
        path_info.local_path: path_info for path_info in alphabetically_sorted_path_infos
    }
    directories_index = {
        path_info.local_path: idx
        for idx, path_info in enumerate(alphabetically_sorted_path_infos)
        if path_info.local_path.is_dir()
    }
    items = peekable(rank_sorted_index_contents)

    # Need this function to be defined here to retain access to data structures

    def _contents_index_iter(
        current_dir: Path = base_dir, current_hierarchy=0
    ) -> typing.Iterator[types_.PathInfo]:
        """Recursively iterates through items by their hierarchy.

        Args:
            current_dir: The directory being processed.
            current_hierarchy: The hierarchy being processed.
        """
        while (next_item := items.peek(None)) is not None:
            # Advance iterator
            item = next_item
            next(items)
            next_item = items.peek(None)

            # Get the path info
            item_path_info = local_path_path_info[base_dir / item.reference_value]
            # Update the navlink title based on the contents index
            item_path_info_dict = item_path_info._asdict()
            item_path_info_dict["navlink_title"] = item.reference_title
            yield types_.PathInfo(**item_path_info_dict)

            # Check for directory
            if item_path_info.local_path.is_dir():
                yield from _contents_index_iter(
                    current_dir=item_path_info.local_path,
                    current_hierarchy=current_hierarchy + 1,
                )

            # Check for last item in the directory
            if next_item is None or next_item.hierarchy < current_hierarchy:
                # Yield all remaining items for the current directory
                path_infos_for_dir = itertools.takewhile(
                    lambda path_info: current_dir in path_info.local_path.parents,
                    alphabetically_sorted_path_infos[directories_index[current_dir] :],
                )
                path_infos_for_dir_not_yielded = filter(
                    lambda path_info: not local_path_yielded[path_info.local_path],
                    path_infos_for_dir,
                )
                yield from side_effect(
                    lambda path_info: local_path_yielded.update(((path_info.local_path, True),)),
                    path_infos_for_dir_not_yielded,
                )

    yield from _contents_index_iter()
    # Yield all items not yet yielded
    yield from filter(
        lambda path_info: not not local_path_yielded[path_info.local_path],
        alphabetically_sorted_path_infos,
    )
