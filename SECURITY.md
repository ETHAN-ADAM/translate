# Security and privacy

smiles转化器 is designed as an offline local application.

## Network

The application source does not perform HTTP requests, telemetry, analytics,
cloud uploads, or automatic update checks.

## Molecular data

SMILES strings are processed locally by RDKit.

By default, exported JSON does not contain `canonical_smiles`.

## Build artifacts

Unsigned Windows executables may trigger Microsoft SmartScreen / Smart App Control.
For public commercial distribution, code signing is recommended.
