# Installing Driftbeam

This guide walks through installing the Driftbeam client library and verifying that your environment is ready for development.
Every install path below is offline-friendly once your package mirror holds the wheels.

## Prerequisites

Driftbeam requires Python 3.10 or newer and a pip installation of version 23.0 or later.
We strongly recommend installing into a virtual environment so that the client's pinned dependencies never interfere with system packages.
A C compiler is only needed if you opt into the native acceleration extras; the default install ships pure-Python wheels.
On restricted networks, mirror the package index internally rather than copying wheel files between machines by hand.

## Installing with pip

The library is published to the Python Package Index under the name driftbeam.
Optional extras are available for the command-line interface and for native acceleration.
Installing the cli extra adds the driftbeam console script to your PATH.

```bash
python -m venv .venv
source .venv/bin/activate
pip install "driftbeam[cli]"
```

## Platform notes

Wheel coverage differs slightly between operating systems, so read the subsection for your platform before filing an installation bug.

### Linux

Prebuilt manylinux wheels cover x86_64 and aarch64, so most distributions install without a compiler.
Musl-based systems such as Alpine fall back to a source build unless the native extras are disabled.

### macOS

On macOS we publish universal2 wheels that run natively on Apple silicon and Intel processors alike.
No translation layer is involved, and the same wheel serves both architectures.

### Windows

Windows installs require the Microsoft Visual C++ Redistributable only when the native extras are enabled.
Enable long path support in the registry before installing into deeply nested project directories.

## Installing from source

Building from source is only necessary when you need an unreleased fix or want to test a patch before it ships.
An editable install picks up local changes without reinstalling.

```bash
git clone https://example.invalid/driftbeam/driftbeam.git
cd driftbeam
pip install -e ".[dev]"
```

## Verifying the installation

Running `driftbeam --version` prints the installed version and the active profile.
If both values appear, the console script and the package agree and the installation is complete.
Import the `driftbeam` package to confirm the interpreter can see it.

```python
import driftbeam

print(driftbeam.__version__)
```

> **Note:** If the import fails with a ModuleNotFoundError, confirm that the interpreter on your PATH is the same one pip installed into.

![Successful verification output](images/install-check.png)

## Upgrading

Driftbeam follows semantic versioning, and patch releases never change public behavior.
Read the changelog before crossing a minor version boundary, because deprecations are announced one minor release in advance.
Pin the minor version in production and move the pin deliberately.

```bash
pip install --upgrade "driftbeam~=1.4"
```
