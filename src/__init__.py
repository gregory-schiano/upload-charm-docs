# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for uploading docs to charmhub."""
import logging
from itertools import tee

from .action import DRY_RUN_NAVLINK_LINK, FAIL_NAVLINK_LINK
from .action import run_all as run_all_actions
from .check import conflicts as check_conflicts
from .clients import Clients
from .constants import DEFAULT_BRANCH, DOCUMENTATION_FOLDER_NAME, DOCUMENTATION_TAG
from .docs_directory import read as read_docs_directory
from .download import recreate_docs
from .exceptions import InputError
from .index import get as get_index
from .navigation_table import from_page as navigation_table_from_page
from .reconcile import run as get_reconcile_actions
from .repository import DEFAULT_BRANCH_NAME
from .types_ import ActionResult, UserInputs

GETTING_STARTED = (
    "To get started with upload-charm-docs, "
    "please refer to https://github.com/canonical/upload-charm-docs#getting-started"
)


def run_reconcile(clients: Clients, user_inputs: UserInputs) -> dict[str, str]:
    """Upload the documentation to charmhub.

    Args:
        clients: The clients to interact with things like discourse and the repository.
        user_inputs: Configurable inputs for running upload-charm-docs.

    Returns:
        All the URLs that had an action with the result of that action.

    Raises:
        InputError: if there are any problems with executing any of the actions.

    """
    if not clients.repository.has_docs_directory:
        logging.warning(
            "Cannot run any reconcile to Discourse as there is not any docs folder "
            "present in the repository"
        )

        return {}

    if clients.repository.is_same_commit(DOCUMENTATION_TAG, user_inputs.commit_sha):
        logging.warning(
            "Cannot run any reconcile to Discourse as we are at the same commit of the tag %s",
            DOCUMENTATION_TAG,
        )
        return {}

    metadata = clients.repository.metadata
    base_path = clients.repository.base_path

    index = get_index(metadata=metadata, base_path=base_path, server_client=clients.discourse)
    path_infos = read_docs_directory(docs_path=base_path / DOCUMENTATION_FOLDER_NAME)
    server_content = (
        index.server.content if index.server is not None and index.server.content else ""
    )
    table_rows = navigation_table_from_page(page=server_content, discourse=clients.discourse)
    actions = get_reconcile_actions(
        path_infos=path_infos,
        table_rows=table_rows,
        clients=clients,
        base_path=base_path,
    )

    # tee creates a copy of the iterator which is needed as check_conflicts consumes the iterator
    # it is passed
    actions, check_actions = tee(actions, 2)
    problems = tuple(
        check_conflicts(
            actions=check_actions, repository=clients.repository, user_inputs=user_inputs
        )
    )
    if problems:
        raise InputError(
            "One or more of the required actions could not be executed, see the log for details"
        )

    reports = run_all_actions(
        actions=actions,
        index=index,
        discourse=clients.discourse,
        dry_run=user_inputs.dry_run,
        delete_pages=user_inputs.delete_pages,
    )
    urls_with_actions: dict[str, str] = {
        str(report.location): report.result
        for report in reports
        if report.location is not None
        and report.location != DRY_RUN_NAVLINK_LINK
        and report.location != FAIL_NAVLINK_LINK
    }

    if not user_inputs.dry_run:
        clients.repository.tag_commit(
            tag_name=DOCUMENTATION_TAG, commit_sha=user_inputs.commit_sha
        )

    return urls_with_actions


def run_migrate(clients: Clients, user_inputs: UserInputs) -> dict[str, str]:
    """Migrate existing docs from charmhub to local repository.

    Args:
        clients: The clients to interact with things like discourse and the repository.
        user_inputs: Configurable inputs for running upload-charm-docs.

    Returns:
        A single key-value pair dictionary containing a link to the Pull Request containing
        migrated documentation as key and successful action result as value.
    """
    if not clients.repository.metadata.docs:
        logging.warning(
            "Cannot run migration from Discourse as there is no discourse "
            "link available in metadata"
        )
        return {}

    logging.info("Tag exists: %s", str(clients.repository.tag_exists(DOCUMENTATION_TAG)))

    if not clients.repository.tag_exists(DOCUMENTATION_TAG):
        with clients.repository.with_branch(DEFAULT_BRANCH) as repo:
            main_hash = repo.current_commit
        clients.repository.tag_commit(DOCUMENTATION_TAG, main_hash)

    pull_request = clients.repository.get_pull_request(DEFAULT_BRANCH_NAME)

    # Check difference with main
    changes = recreate_docs(clients, DOCUMENTATION_TAG)
    if not changes:
        logging.info(
            "No community contribution found in commit %s. Discourse is inline with %s",
            user_inputs.commit_sha,
            DOCUMENTATION_TAG,
        )
        # Given there are NO diffs compared to the base, if a PR is open, it should be closed
        if pull_request is not None:
            pull_request.edit(state="closed")
        return {}

    if pull_request is not None:
        logging.info(
            "upload-charm-documents pull request already open at %s", pull_request.html_url
        )
        clients.repository.update_pull_request(DEFAULT_BRANCH_NAME)
    else:
        logging.info("PR not existing: creating a new one...")
        pull_request = clients.repository.create_pull_request(DOCUMENTATION_TAG)

    return {pull_request.html_url: ActionResult.SUCCESS}
