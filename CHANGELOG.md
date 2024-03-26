# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),

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
