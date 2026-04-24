# RFC: Enforce Local Custom Mount Boundaries After Symlink Resolution

## Summary

Local sandbox custom mounts should validate resolved filesystem paths against their configured mount roots before any read or write operation.

The current implementation accepts custom mount virtual paths by prefix, then resolves them to host paths. If the mounted directory contains a symlink to an outside path, file operations can escape the intended mount boundary. Read-only checks can also be bypassed because the resolved target no longer appears to be inside the read-only mount.

## Problem

Custom mounts are useful for exposing trusted host directories to local sandbox tools. They are also a boundary: a path under `/mnt/data` should not be able to access arbitrary host paths unless that path is inside the configured host root.

A risky sequence:

1. Configure a read-only custom mount from `/host/data` to `/mnt/data`.
2. `/host/data/link` is a symlink to `/tmp/outside`.
3. The agent calls `write_file("/mnt/data/link/out.txt", ...)`.
4. The virtual prefix check accepts `/mnt/data/...`.
5. Local path resolution follows the symlink to `/tmp/outside/out.txt`.
6. The read-only check no longer sees the resolved path as inside `/host/data`, so the write can proceed.

The same issue can affect read, list, glob, grep, update, and command path resolution depending on how a symlink is reached.

## Affected Code

- `backend/packages/harness/deerflow/sandbox/tools.py`
- `backend/packages/harness/deerflow/sandbox/local/local_sandbox.py`
- `backend/packages/harness/deerflow/sandbox/local/local_sandbox_provider.py`

## Goals

- Ensure a custom mount path cannot escape its configured host root after symlink resolution.
- Enforce `read_only` based on the matched custom mount, not only on the final resolved target.
- Preserve support for legitimate symlinks that resolve inside the same mount root.
- Add regression tests for symlink escape and read-only bypass.

## Non-Goals

- Treat `LocalSandboxProvider` as a secure isolation boundary for arbitrary host bash.
- Change the public custom mount config schema.
- Remove support for custom mounts.

## Proposal

Add a custom mount resolver that returns both:

- the matched `PathMapping`
- the resolved host path

For every file operation on a custom mount:

1. Match the virtual path to the longest container path prefix.
2. Join the relative path to the mount's host root.
3. Resolve the candidate path.
4. Verify `candidate.relative_to(mount_root.resolve())`.
5. Reject if the candidate escapes the mount root.
6. If the operation writes and the matched mount is read-only, reject before opening the file.

The read-only decision should come from the matched mapping. It should not depend on whether the symlink target is still under that mapping.

Command path rewriting should apply the same resolver before executing host commands in local mode.

## Testing

Add tests covering:

- Read-only mount with `link -> outside`: write is rejected.
- Writable mount with `link -> outside`: write is rejected because it escapes the mount root.
- Symlink inside the mount root: read/write behavior follows the mount's read-only flag.
- `glob` and `grep` do not return paths outside the custom mount through symlink traversal.

## Open Questions

- Should custom mounts default to not following symlinks at all, or allow symlinks that stay inside the mount root?
- Should error messages expose that a symlink escape was detected, or use the existing generic permission-denied wording?
