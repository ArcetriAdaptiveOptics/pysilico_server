# PYSILICO server: Prosilica AVT camera controller for Plico

 ![Python package](https://github.com/ArcetriAdaptiveOptics/pysilico_server/workflows/Python%20package/badge.svg)
 [![codecov](https://codecov.io/gh/ArcetriAdaptiveOptics/pysilico_server/branch/master/graph/badge.svg?token=04PRSBMW11)](https://codecov.io/gh/ArcetriAdaptiveOptics/pysilico_server)
 [![Documentation Status](https://readthedocs.org/projects/pysilico_server/badge/?version=latest)](https://pysilico_server.readthedocs.io/en/latest/?badge=latest)
 [![PyPI version][pypiversion]][pypiversionlink]



pysilico is an application to control [Allied AVT/Prosilica][allied] cameras (and possibly other GigE cameras) under the [plico][plico] environment.

## Baumer Camera Support

This server now supports Baumer VCX cameras through the `neoapi` SDK. Key features include:

*   **Pixel Format Configuration**: Prioritizes `Mono12`, then `BGR8`, and falls back to `Mono8` based on camera availability.
*   **Region of Interest (ROI) Management**: Supports defining and acquiring frames from multiple ROIs. Individual ROI frames can be accessed, and the camera can be reverted to full-frame acquisition.

See [pysilico][pysilico] for installation and usage

[plico]: https://github.com/ArcetriAdaptiveOptics/plico
[pysilico]: https://github.com/ArcetriAdaptiveOptics/pysilico
[allied]: https://www.alliedvision.com
[travis]: https://travis-ci.com/ArcetriAdaptiveOptics/pysilico_server.svg?branch=master "go to travis"
[travislink]: https://travis-ci.com/ArcetriAdaptiveOptics/pysilico_server
[coveralls]: https://coveralls.io/repos/github/ArcetriAdaptiveOptics/pysilico_server/badge.svg?branch=master "go to coveralls"
[coverallslink]: https://coveralls.io/github/ArcetriAdaptiveOptics/pysilico_server
[pypiversion]: https://badge.fury.io/py/pysilico-server.svg
[pypiversionlink]: https://badge.fury.io/py/pysilico_server
