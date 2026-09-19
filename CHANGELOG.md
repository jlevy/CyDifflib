# Changelog

## [Unreleased]
### Changed
- require Cython 3.3+ so free-threaded Python 3.14 can compile
- mark the extension free-threading compatible (one SequenceMatcher per thread;
  HtmlDiff's shared prefix counter is locked)
- add support for Python 3.14 and 3.14t
- allow CMake 3.15 through 3.30

## [1.2.0] - 2025-04-11
### Changed
- drop support for Python 3.8
- drop support for Python 3.9
- add support for Python 3.13
- switch from `scikit-build` to `scikit-build-core`

## [1.1.0] - 2024-02-03
### Changed
- drop support for Python 3.6
- drop support for Python 3.7
- add support for Python 3.12
