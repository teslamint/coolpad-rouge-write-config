# 1. Use PyUSB for the fastboot transport

Date: 2026-10-12

## Status

Accepted

## Context

The stock fastboot CLI does not expose an arbitrary vendor command interface.
The bootloader expects the exact command `write-config:VALUE`.

A patched platform-tools fork would add a large maintenance surface.
The tool needs only three fastboot commands and no data phase.

The client must prevent accidental commands to another device.
It must also prevent callers from sending other hidden commands.

## Decision

The client uses PyUSB to send the standard USB fastboot frames.
The code imports PyUSB only after all local safety checks pass.

The public interface accepts only values 0 and 1.
It requires an exact USB serial and a device acknowledgement token.

The client checks `getvar:product` and `getvar:serialno` before the write.
It rejects every product except `3320A`.
It rejects every USB vendor identifier except `0x1ebf`.

## Consequences

The tool does not require an Android platform-tools fork.
The transport remains small enough for direct review.

Users must install PyUSB and a supported libusb backend.
Operating-system USB permissions remain outside this repository.

The synthetic tests can replace PyUSB without a physical device.
The tests cannot prove behavior on every host USB stack.
