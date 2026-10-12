# Security policy

## Supported versions

Only the latest release receives security fixes.

## Report a vulnerability

Use GitHub Security Advisories for private reports.
Do not include device dumps, serial numbers, keys, or proprietary firmware.

## Device safety boundary

This program changes one byte in the device `config` partition.
A power loss or transport fault can leave the result unknown.

The program cannot prove that a device is recoverable.
Create a verified partition backup before any physical-device execution.

The project tests only a simulated fastboot transport.
No release test writes to a physical device.
