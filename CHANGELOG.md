# Changelog

## [Unreleased]

## [v0.2.2] - 2023-01-23

### Fixed

- Name clashes during migration for checkouts when a file or directory has the
  same name as the branch being checked out

### Changed

- The action now operates in a temporary directory that is a copy of the
  directory the action was called on. Using a temporary directory ensures that
  any operations of the action, such as git operations, do not change the state
  of the files and directories any following steps receive.

## [v0.2.1] - 2023-01-20

### Fixed

- Migration now correctly handles that the git checkout on GitHub actions runs
  in detached head mode, the migration failed before due to not being able to
  create a new branch from detached head mode
- Only files in the `docs` directory are now added to the migration PR
- The migration PR is now created with a branch from the default branch merging
  back into the default branch, previously the branch was from the branch the
  action was running on back into that branch

## [v0.2.0] - 2023-01-13

### Added

- Topics are now created unlisted on discourse
- Runs on a charm with existing documentation and without the `docs` directory
  now results in a PR being created to migrate the docs to the repository

## [v0.1.1] - 2022-12-13

### Fixed

- Resolve bug where the presence of a topic on the server was not checked

### Fixed

- Allow redirects for topic retrieval which is useful if the slug is
  incorrectly or not defined

## [v0.1.0] - 2022-12-07

### Added

- Copying files from source to discourse
- Dry run mode to see changes that would occur without executing them
- Option to skip deleting topics from discourse

[//]: # "Release links"
[0.1.1]: https://github.com/canonical/upload-charm-docs/releases/v0.1.1
[0.1.0]: https://github.com/canonical/upload-charm-docs/releases/v0.1.0