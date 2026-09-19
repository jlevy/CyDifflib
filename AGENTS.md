# CyDifflib Agent Instructions

This file follows the [AGENTS.md](https://agents.md) convention.
Claude Code reads `CLAUDE.md`, which imports this file through its `@AGENTS.md` line.

## Build and Test

Cython/C++ extension via **scikit-build-core** and **CMake**.

Published installs and GitHub Actions use pip and cibuildwheel.
Do not switch CI to uv.

Local work: use uv with the checked-in `uv.toml` if present.

```bash
UV_CONFIG_FILE=uv.toml uv sync --python 3.13 --all-groups --reinstall-package cydifflib
UV_CONFIG_FILE=uv.toml uv run --python 3.13 pytest
```

Default local interpreter is 3.13.
Also test 3.11, 3.12, 3.14, and 3.14t (`3.14` is GIL, `3.14t` is free-threaded).

End-to-end from an installed interpreter (import + the same pytest suite CI runs
after each wheel install):

```bash
for py in 3.11 3.12 3.13 3.14 3.14t; do
  UV_CONFIG_FILE=uv.toml uv run --python "$py" python -c "import cydifflib; print(cydifflib.SequenceMatcher(None, 'abcd', 'bcde').ratio())"
  UV_CONFIG_FILE=uv.toml uv run --python "$py" pytest
done
```

3.9, 3.10, and PyPy are CI-only.

Wheel jobs in `build.yml` set `CIBW_TEST_REQUIRES=pytest` and
`CIBW_TEST_COMMAND=pytest {package}/tests`. That installs the built wheel, then
runs `tests/` (including `test_gil_stays_disabled` on free-threaded tags).
Skips:

- Linux: `*_{aarch64,ppc64le,s390x}` and `*musllinux_*` (build only)
- Windows: `*-win32` (build only); `win_arm64` is cross-compiled on `windows-latest`
- macOS: `pp*-macosx_*` (build only)

The sdist job generates `.cxx`, strips Cython from `build-system.requires`,
installs the tarball, and runs pytest. Linux wheel tags are `cp39`–`cp314`,
`cp314t`, and `pp39`–`pp311`. macOS/Windows also build cibuildwheel extras
`cp315` / `cp315t` because those jobs do not set `CIBW_BUILD`.

Isolated wheel and sdist:

```bash
UV_CONFIG_FILE=uv.toml uv build --python 3.13
```

Sdist with generated C++ and Cython stripped from `build-system.requires`:

1. Generate `.cxx`:
   `UV_CONFIG_FILE=uv.toml uv run --python 3.13 --with "Cython>=3.3.0,<3.4" ./src/cydifflib/generate.sh`
2. `cp pyproject.toml .pyproject.toml.sdist.bak`
3. `git apply ./tools/sdist.patch`
4. `UV_CONFIG_FILE=uv.toml uv build --python 3.13 --sdist`
5. `mv .pyproject.toml.sdist.bak pyproject.toml`

## Conventions

- **Layout:** `src/` (`src/cydifflib/`, tests in `tests/`)
- **Python:** published wheels still support 3.9+; local default is 3.13
- **Build:** Cython `>=3.3.0,<3.4` is build-only; do not list cmake or ninja in
  `build-system.requires`
- **Version:** `src/cydifflib/__init__.py` (read at build time)
- **Free-threading:** `_initialize.pyx` sets `freethreading_compatible=True`;
  `HtmlDiff._default_prefix` is locked; use one `SequenceMatcher` per thread
- **Lint:** do not run a repository-wide format of the `.pyx` sources

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
