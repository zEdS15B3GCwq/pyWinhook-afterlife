# pyWinhook-afterlife

**WORK IN PROGRESS** pyWinhook builds for CPython 3.12+, and limited abi3 (3.11+).

## What this project is for

The project [pyWinhook](https://github.com/Tungsteno74/pyWinhook) by Tungsteno,
which built on [pyHook](http://pyhook.sourceforge.net/) by Peter Parente, does
not have any wheels for CPython versions 3.12 and above
([PyPI](https://pypi.org/project/pyWinhook/#files)).

Trying to install it on a recent Python version requires building from source,
but that fails without fixes. As a result, packages that define pyWinhook as a
dependency, such as PsychoPy, cannot be installed.

This project provides builds of pyWinhook that can be installed on recent
Python versions. The builds can be trusted not to contain malware or any
modifications to the source other than the fixes.

The _afterlife_ postfix in the project name was chosen to reflect that the
pyWinhook repository has been inactive (dead?) for a while now, and this
project does not intend to revive it, beyond the scope of making installation
possible. The wheels here are built from the same source code as the original,
and as such, any issues beyond installation are out of scope for this project.

pyWinhook has a recent PR ([#21](https://github.com/Tungsteno74/pyWinhook/pull/21))
which applies the same fix plus adds a `pyproject.toml`. Perhaps it will be
merged in the future.

## Fixes and changes

pyWinhook uses the legacy Python 2 functions `PyInt_Aslong(x)` that do not
exist on Python 3. It only used to work because older versions of SWIG defined
Python 3 aliases for these functions, but those were removed in SWIG versions
4.5.0 and later.

The fix is simple: one can either correct the legacy references by replacing
them in the source code (or providing alias definitions), or by using an
earlier version of SWIG.

I opted for the former, which means that 2 references to `PyInt_AsLong` in
`cpyHook.i` were replaced by `PyLong_AsLong`. Builds that are specific to a
single Python version, such as `cp312_cp312` have been built with only these
changes.

The limited ABI3 build (`cp311_abi3`), which is compatible with any Python 3
version including and above 3.11, required a few additional changes in
`setup.py` to change how the wheel was built. This is not a change to the
source code, just the build parameters.

Changes from the original source can be verified at the following links. Each
link points to a specific commit that the wheels were built from:

* Fixes: [fix commit vs original diff](https://github.com/Tungsteno74/pyWinhook/compare/master...zEdS15B3GCwq:pyWinhook:1afa209973a0d795ab2015732e76dd8099a5ca74)
* Fixes + ABI3 setup: [fix-abi3 commit vs original diff](https://github.com/Tungsteno74/pyWinhook/compare/master...zEdS15B3GCwq:pyWinhook:63dc0e69cb279a133629314cf5ac5aa121f869d)

## Attestation

The build process takes place entirely on GitHub, using the workflow
[build.yml](https://github.com/zEdS15B3GCwq/pyWinhook-afterlife/blob/ci/initial/.github/workflows/build.yml),
providing
[attestation](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations),
which basically means that the wheels were really built from the commits with
the changes described above, and that no malicious code was sneaked in during
the build process.

## Installation

Two types of wheels are provided:

* Files with a name like `pywinhook-1.6.2-cp315-cp315-win_amd64.whl` are built
  for one specific version of Python. In this particular example, for CPython
  3.15.
* There is one ABI3 build, `pywinhook-1.6.2-cp311-abi3-win_amd64.whl`, which
  is compatible with any Python 3 version including and beyond 3.11. This build
  is more flexible but may not be as performant as the version-specific builds.

Wheels can be downloaded, or directly installed from the
[Releases](https://github.com/zEdS15B3GCwq/pyWinhook-afterlife/releases):

```cmd
<examples>
```
