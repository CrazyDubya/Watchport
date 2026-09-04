# Contributing to Watchport

Watchport is security-sensitive despite its intentionally small scope.

Before contributing:

1. read `AGENTS.md`
2. read `docs/SECURITY.md`
3. identify which trust boundary your change affects
4. keep changes narrow and testable

## Pull requests

A good PR should state:

- what behavior changes
- why the change is needed
- security invariants touched
- tests performed
- dependencies added/changed
- known limitations

Do not bundle unrelated refactoring with authentication, session, streaming, or indicator changes.

## Security-sensitive changes

Changes that add or expose remote authority—input, clipboard, files, commands, microphone, power control, public ingress, or persistent tokens—require an explicit architecture/security decision before implementation.

## Dependencies

Record new dependencies in `docs/LICENSING.md` with their license and integration form.

## Security reports

Until a dedicated private reporting channel is configured, avoid publishing exploit details for a live vulnerability in an issue. Contact the repository owner privately through an available GitHub channel first.
