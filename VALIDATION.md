# Validation status

## Hardware result

The original procedure on one RMX3241 / F.12 / LATAM completed Magisk setup/reboot
and returned UID 0. It used the working DA/container/source revisions pinned here.
The complete hardware history and uncertainty about the earlier seccfg experiment
are recorded in `docs/case-study.md`.

## Repository validation

- Pinned tool downloads completed from their sources and all release/stage hashes matched.
- Rebuilt DA container matched SHA256 `1933ec9b700f2e02bb9a018b97c47e6b11d6d0a36a1c1c8f4b8d1c40e27e985d`.
- The original private GPT was parsed offline and its boot geometry matched the observed case.
- The original/patched private preloaders passed signed-payload preservation checks offline.
- Unit tests cover identity/build/region refusal, actual unlock prerequisites, corrupt/truncated
  and overlapping GPTs, the exact documented MTK recovery quirk, checksum/ZIP rejection,
  preloader preservation, dry-run boundaries, and image/tool changes after planning.
- A public-tree scan rejects tracked private artifacts and common credential patterns.

No private GPT/image fixture is published. Synthetic fixtures are used in CI.
The new helpers have not been replayed through another hardware flash/unlock/wipe.
Local verification establishes the listed behavior, not universal rooting compatibility.

Run `make check`. GitHub Actions repeats offline checks on Python 3.11 and 3.14.
