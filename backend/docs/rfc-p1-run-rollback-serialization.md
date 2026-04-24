# RFC: Serialize Run Interrupt and Rollback Cleanup

## Summary

DeerFlow should treat interrupted or rolling-back runs as still in flight until their worker task has actually stopped and any checkpoint rollback has completed.

Today a run can be marked `interrupted` before the old worker finishes cleanup. A new run for the same thread may start during that gap and write a fresh checkpoint, then the old rollback can restore an older snapshot over it.

## Problem

The runtime run manager exposes `multitask_strategy=interrupt` and `multitask_strategy=rollback` so callers can replace work already running on a thread.

The risky sequence is:

1. Run A is executing on thread T.
2. A cancel, interrupt, or rollback request arrives.
3. Run A is marked as terminal or no longer considered active.
4. Run B is accepted for the same thread.
5. Run B writes new state/checkpoints.
6. Run A's worker reaches its cancellation cleanup and performs rollback.
7. The rollback restores Run A's previous snapshot over Run B's state.

This is a state consistency bug, not only a reporting bug. The user can observe a successful newer run whose thread state later reverts.

## Affected Code

- `backend/packages/harness/deerflow/runtime/runs/manager.py`
- `backend/packages/harness/deerflow/runtime/runs/worker.py`
- Checkpointer rollback paths used by run cancellation cleanup

## Goals

- Prevent more than one mutable run cleanup path from touching the same thread state at a time.
- Ensure rollback cannot overwrite a checkpoint created by a newer run.
- Keep current interrupt and rollback semantics for callers, but make the internal lifecycle explicit.
- Add regression tests that fail under delayed cancellation/rollback.

## Non-Goals

- Redesign the public run API.
- Change checkpoint storage format.
- Add distributed locking across multiple machines in the first patch.

## Proposal

Introduce non-terminal lifecycle states such as:

- `cancelling`
- `rolling_back`

A run in either state must still count as in flight for the thread. The run manager should not accept a new mutable run for the same thread until the old worker has completed cancellation cleanup and rollback.

Recommended behavior:

1. `cancel()` and replacement strategies request cancellation and move the old run into `cancelling` or `rolling_back`.
2. The old run remains in the active/inflight index for its thread.
3. The worker performs rollback, emits final status, and only then transitions to a terminal state.
4. The run manager removes the run from the thread inflight index only after worker cleanup completes.
5. New runs for the same thread wait, reject, or queue according to the selected strategy.

If waiting is not desirable for the HTTP request path, the API can return a clear conflict while the previous run is still cleaning up.

## Testing

Add a fake checkpointer/worker test that controls timing:

1. Start Run A and let it reach a checkpoint.
2. Trigger rollback with an artificial delay before rollback finishes.
3. Attempt to start Run B during that delay.
4. Assert Run B is not allowed to write until Run A cleanup completes.
5. Assert final checkpoint/state belongs to Run B only after Run B actually runs.

Also add a test for `interrupt` without rollback so the lifecycle rule is consistent.

## Open Questions

- Should replacement requests wait for cleanup or return conflict immediately?
- Should thread-level serialization live in the run manager only, or also in the checkpointer as a final guard?
