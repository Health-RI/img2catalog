# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),

## 1.0.0

### Updated
## [v2.0.0] - 2025-09-04

### Added
- fix: implement review comments by @Alexander Harms in d37dfcc
- fix: implements review comments by @Alexander Harms in 2a6d89c
- feat: updates xnat custom form by @Alexander Harms in 23287c0
- feat: adds fallback keywords in case of none found by @Alexander Harms in 5d90466
- feat: adds support for xnat custom forms by @Alexander Harms in 5ae7619
- feat: make cli more modular add include_private flag by @Alexander Harms in 0e41f14
- feat: makes cli modular by @Alexander Harms in 5dde34d
- feat: update to health-ri v2 by @Alexander Harms in ed765eb
- fix: implement review comments by @Alexander Harms in c10a198
- fix: implements review comments by @Alexander Harms in bf19cde
- feat: updates xnat custom form by @Alexander Harms in de09eca
- feat: adds fallback keywords in case of none found by @Alexander Harms in 275867d
- feat: adds support for xnat custom forms by @Alexander Harms in f9ac988
- feat: make cli more modular add include_private flag by @Alexander Harms in 3f54202
- feat: makes cli modular by @Alexander Harms in 7fc43d3
- feat: update to health-ri v2 by @Alexander Harms in f3454bf
- feat: support multiple publishers (#63) by @kburger in 4b43b99


### Changed
- docs: clarifies entries in form JSON by @Alexander Harms in 033a345
- docs: update readme by @Alexander Harms in 4b21b11
- tests: increases test coverage by @Alexander Harms in 3c9392c
- docs: update readme by @Alexander Harms in 68cbf1c
- test: add mapping test without keywords by @Alexander Harms in cc1c6a7
- ci: adds sonar-project.properties by @Alexander Harms in 742299d
- ci: adds updated test and release workflows by @Alexander Harms in 907b0c0
- Refactor (#64) by @Alexander Harms in a24084f
- docs: clarifies entries in form JSON by @Alexander Harms in cee5830
- docs: update readme by @Alexander Harms in 08ba5e2
- tests: increases test coverage by @Alexander Harms in dcbe000
- ci: adds sonar-project.properties by @Alexander Harms in 6d9c6a5
- ci: adds updated test and release workflows by @Alexander Harms in 9548eeb
- Bump pypa/gh-action-pypi-publish from 1.12.3 to 1.12.4 by @dependabot[bot] in dab5ec1
- docs: update readme by @Alexander Harms in a974f8c
- test: add mapping test without keywords by @Alexander Harms in cc33ad2
- Refactor (#64) by @Alexander Harms in 2624490


### Fixed
- fix: fixes whitelines at EOF by @Alexander Harms in 7afdb42
- Fix/small fixes (#71) by @Alexander Harms in 306ffa7
- fix(ci): fix ci dependencies by @Alexander Harms in fe9ab64
- fix(ci): publish pypi on workflow dispatch, test on PR ready to review (#67) by @Alexander Harms in 9c69b67
- fix(tests): removes linenumber refs from docstrings by @Alexander Harms in a88f1c2
- fix: updates sempyro dependency by @Alexander Harms in e7070cb
- fix: textarea for version_notes would cause too much recursion error by @Alexander Harms in 4c2d64e
- fix: qualified attribution should be an agent not an URI by @Alexander Harms in 47a5a82
- Revert "fix: filtering of empty form content turned out to be unnecessary" by @Alexander Harms in 32a0e9e
- fix: filtering of empty form content turned out to be unnecessary by @Alexander Harms in a25c351
- fix: removes integration test for private projects by @Alexander Harms in f33e14b
- fix: removes harvesting from private projects by @Alexander Harms in 9aa82fa
- fix: removes old test for health-ri v1 by @Alexander Harms in 39dc698
- fix: upgrades SeMPyRO to v2.0.1 by @Alexander Harms in eb6908f
- fix: remove unused commented out code by @Alexander Harms in 3584ccb
- fix: add mailto: prefix to example emails by @Alexander Harms in 17f9bee
- fix(tests): adds reference for integration test with private projects by @Alexander Harms in bc773d0
- fix(tests): integration tests for private projects by @Alexander Harms in f1cff29
- fix(tests): integration tests for private projects by @Alexander Harms in 2948b93
- fix: flow of unmapped and mapped objects in CLI by @Alexander Harms in 6c480c5
- fix: update version and required sempyro version by @Alexander Harms in dacb153
- fix(tests): fixes test now that publisher identifier is a list in the example config by @Alexander Harms in 9fd019c
- fix(ci): fixes missing quote by @Alexander Harms in 5a975ed
- Fix/small fixes (#71) by @Alexander Harms in 4888b78
- fix(ci): fix ci dependencies by @Alexander Harms in 9ca61ce
- fix(ci): publish pypi on workflow dispatch, test on PR ready to review (#67) by @Alexander Harms in a8167e5
- fix(tests): removes linenumber refs from docstrings by @Alexander Harms in 76dcacd
- fix: updates sempyro dependency by @Alexander Harms in 8b3f678
- fix: textarea for version_notes would cause too much recursion error by @Alexander Harms in e9acecd
- fix: qualified attribution should be an agent not an URI by @Alexander Harms in 6645dd2
- Revert "fix: filtering of empty form content turned out to be unnecessary" by @Alexander Harms in 91587bb
- fix: filtering of empty form content turned out to be unnecessary by @Alexander Harms in 2f256a6
- fix: removes integration test for private projects by @Alexander Harms in 7d5425b
- fix: removes harvesting from private projects by @Alexander Harms in 346880c
- fix(ci): fixes missing quote by @Alexander Harms in af76c16
- fix: removes old test for health-ri v1 by @Alexander Harms in 8a80979
- fix: upgrades SeMPyRO to v2.0.1 by @Alexander Harms in 55312a0
- fix: remove unused commented out code by @Alexander Harms in 684c20f
- fix: add mailto: prefix to example emails by @Alexander Harms in 9f5e3e9
- fix(tests): adds reference for integration test with private projects by @Alexander Harms in bdb4fa6
- fix(tests): integration tests for private projects by @Alexander Harms in 712202d
- fix(tests): integration tests for private projects by @Alexander Harms in 598cbf4
- fix: flow of unmapped and mapped objects in CLI by @Alexander Harms in ee1c0a7
- fix: update version and required sempyro version by @Alexander Harms in de67b45
- fix(tests): fixes test now that publisher identifier is a list in the example config by @Alexander Harms in 4ed09d0


### Removed
- tests: removes unnecessary test by @Alexander Harms in c61c9e7
- tests: removed unused statements from test configuration by @Alexander Harms in 94fd8d2
- tests: removes unnecessary test by @Alexander Harms in 60bb320
- tests: removed unused statements from test configuration by @Alexander Harms in 3a60734



* Dependencies have been updated

### Added

* The environment variable `IMG2CATALOG_SPARQL_ENV` can now be used to set the SPARQL endpoint
* The opt-in keyword can now be excluded from the generated DCAT with a configuration setting

### Changed

* All investigators are added as creator
* HTML characters in the XNAT description are unescaped

### Fixed

* img2catalog now uses the latest [SeMPyRO](https://github.com/health-RI/sempyro). This changes
the VCard definition used for contactpoint.
* Test coverage has been improved

### Removed

* The built-in FDP client was moved to the external library [fairclient](https://github.com/health-RI/fairclient)

## 0.4.0 - 2024-07-23

### Added

* Datasets can now be updated in a FAIR Data Point if it exposes a SPARQL endpoint
* Automated releases straight from Github

### Changed

* Changed the DCAT generation part to use [SeMPyRO](https://github.com/health-RI/sempyro), a Python DCAT library.

## 0.3.1 - 2024-03-26

### Fixed

* Failure to run the package from PyPI if there was no configuration file present

## 0.3.0 - 2024-02-26

### Added

* The tool can now push Datasets to a FAIR Data Point (FDP)
* A (generic) contact_point can now be added to Datasets, see the example configuration file
* Test coverage was upped a bit more

### Changed

* The tool is now renamed to img2catalog
* The commandline-interface (CLI) is changed heavily and now based on the Click framework

### Fixed

* Under certain circumstances, projects that were not supposed to be indexed were actually indexed

## 0.2.1 - 2024-01-24

### Added

* Logging functionality, a logfile will be stored in the rootfolder
* Multiple XNAT parser errors will be collected for the same project at once, to allow for easy fixing
* Allow usage of environment variable for specifying the xnat server and login details
* Keyword based opt-in and opt-out
* Codecov integration on the repository
* Unit testing added to the github actions code repository

### Changed

* Private projects are now blocked from being indexed

### Fixed

* Fixes empty XNAT keyword bug by applying string strip
* xnatpy session is now put in context manager

## 0.0.2 - 2023-11-06

### Added

* An encompassing catalog will now be created under which all datasets will fall
* A warning message will be displayed if no configuration file could be found
* Test coverage was upgraded

### Fixed

* Testing matrix is fixed to test against all supported python versions
* Python 3.8 compatibility is restored
* Configuration file support in the home directory is fixed for Windows platforms
* A typo in the DCAT output was fixed: catalog --> Catalog

## 0.0.1 - 2023-10=-5

* Initial release
