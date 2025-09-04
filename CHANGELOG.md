# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),

## [v2.0.0] - 2025-09-04

### Added
- feat: adds fallback keywords in case of none found by @Alexander Harms in 5d90466
- feat: adds support for xnat custom forms by @Alexander Harms in 5ae7619
- feat: makes cli modular by @Alexander Harms in 5dde34d
- feat: update to health-ri v2 by @Alexander Harms in ed765eb
- feat: support multiple publishers (#63) by @kburger in 4b43b99


### Changed
- docs: update readme by @Alexander Harms in 4b21b11
- tests: increases test coverage by @Alexander Harms in 3c9392c
- ci: adds sonar-project.properties by @Alexander Harms in 742299d
- ci: adds updated test and release workflows by @Alexander Harms in 907b0c0
- Refactor (#64) by @Alexander Harms in a24084f
- Bump pypa/gh-action-pypi-publish from 1.12.3 to 1.12.4 by @dependabot[bot] in dab5ec1


### Fixed
- fix(ci): fix ci dependencies by @Alexander Harms in fe9ab64
- fix(ci): publish pypi on workflow dispatch, test on PR ready to review (#67) by @Alexander Harms in 9c69b67
- Revert "fix: filtering of empty form content turned out to be unnecessary" by @Alexander Harms in 32a0e9e
- fix: removes old test for health-ri v1 by @Alexander Harms in 39dc698
- fix: upgrades SeMPyRO to v2.0.1 by @Alexander Harms in eb6908f
- fix: remove unused commented out code by @Alexander Harms in 3584ccb
- fix: add mailto: prefix to example emails by @Alexander Harms in 17f9bee
- fix(ci): publish pypi on workflow dispatch, test on PR ready to review (#67) by @Alexander Harms in a8167e5
- fix(tests): removes linenumber refs from docstrings by @Alexander Harms in 76dcacd


### Removed
- tests: removes unnecessary test by @Alexander Harms in c61c9e7
- tests: removed unused statements from test configuration by @Alexander Harms in 94fd8d2

## 1.0.0

### Updated

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
