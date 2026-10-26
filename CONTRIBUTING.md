# Contributing

Run `make check` before submitting a change. Tests must use synthetic fixtures or
mock device boundaries; automated tests must never unlock, wipe, patch a connected
phone, or flash hardware.

For tool updates, include the upstream URL, exact revision/release, SHA256 and why
the change is compatible. Do not replace pinned dependencies with `latest` silently.
For a new device, provide a separate profile and redacted hardware evidence; do not
weaken the existing model/build/region checks. Keep readback/GPT rejection paths tested.

Documentation should state what was observed, what is inferred, and what has not been
hardware-tested. Keep Arabic and English execution guides consistent. No private
images, proprietary DA redistribution, personal identifiers or downloaded tool archives
belong in Git or release assets.
