# Coolpad Rouge `write-config` Client Specification

Date: 2026-10-12

## Status

Proposed for the first public release.

## Scope

The client sends one hidden fastboot command to a Coolpad Rouge 3320A.
The command is either `write-config:0` or `write-config:1`.

The client does not expose an arbitrary fastboot command interface.
The client does not transfer firmware images.
The client does not reboot, erase, unlock, or flash a named partition.

## Reverse-engineered device behavior

The source image is the acquired 3320A `aboot.img` with this SHA-256 value:

`ade1127757a40588a449459353928ba0658cad658ad9e20bd2e04eb0984c5296`

The bootloader registers `write-config:` with the standard fastboot dispatcher.
The command suffix supplies one byte.
The handler treats ASCII `1` as value 1.
The handler treats every other byte as value 0.

The handler reads the final 512-byte sector of the `config` partition.
It changes the final byte of that sector.
It writes the complete sector back to the same address.

The client restricts the suffix to ASCII `0` or ASCII `1`.
The client does not assign a meaning to the stored bit.

## Command-line interface

The package installs `coolpad-rouge-write-config`.

```text
coolpad-rouge-write-config \
  --serial SERIAL \
  --value {0,1} \
  [--execute] \
  [--acknowledge TOKEN]
```

Without `--execute`, the client prints a JSON plan.
Plan mode does not enumerate or open USB devices.

Execution requires this exact acknowledgement token:

```text
WRITE-CONFIG:3320A:SERIAL:VALUE
```

`SERIAL` and `VALUE` match the other arguments.
The client rejects a missing or different token before USB access.

The serial must match `[A-Za-z0-9._-]{1,64}`.
The client never selects a device by position or enumeration order.

## USB and fastboot contract

The client uses a USB interface with these fastboot identifiers:

- Interface class: `0xff`
- Interface subclass: `0x42`
- Interface protocol: `0x03`
- One bulk OUT endpoint
- One bulk IN endpoint

The USB serial descriptor must equal `--serial`.
The USB vendor identifier must equal `0x1ebf`.
Exactly one matching interface must exist.

The client sends these commands in this order:

1. `getvar:product`
2. `getvar:serialno`
3. `write-config:VALUE`

The product response must equal `3320A`.
The fastboot serial response must equal `--serial`.

Each command is 64 ASCII bytes or fewer.
The client accepts `INFO` responses before a final response.
The final response must start with `OKAY` or `FAIL`.
The client rejects `DATA` for all three commands.

The write response must match this expression:

```text
^sz:524288, arg:0, tag:(48|49)$
```

The tag must equal the ASCII code for the requested value.
This response confirms only that the bootloader write helper returned zero.
It does not read the byte back or prove durable storage.

## Exit status and output

The client writes one JSON object to standard output.
It writes a concise error to standard error.

- Exit 0: plan created or the bootloader accepted the write request.
- Exit 2: invalid command-line input.
- Exit 3: device identity or USB selection failed.
- Exit 4: fastboot rejected a preflight command.
- Exit 5: transport or protocol failed before the write command.
- Exit 6: the write command was sent, but confirmation was invalid or absent.

Exit 6 means the device state is unknown.
This includes a `FAIL` response after the write command was sent.
The user must inspect the device before another write attempt.

The JSON output includes the serial, product, requested value, and command state.
The output excludes raw USB descriptors and unrelated device data.

## Safety invariants

1. Plan mode never imports the USB backend.
2. Invalid input never imports the USB backend.
3. The client requires an exact USB serial.
4. The client requires the USB vendor identifier `0x1ebf`.
5. The client requires the exact product value `3320A`.
6. The client requires the fastboot serial to match the USB serial.
7. The client generates only `write-config:0` or `write-config:1`.
8. The client sends no data phase.
9. The client reports an unacknowledged write as indeterminate.
10. Tests never contact a physical USB device.

## Test contract

The end-to-end tests start the real command-line module in a child process.
A fake PyUSB package supplies deterministic devices and fastboot responses.
The fake package records every command in a JSON transcript.

The suite covers plan mode, acknowledgement checks, identity checks, responses,
timeouts, duplicate matches, and write confirmation.

The suite writes `.artifacts/e2e-results.json`.
This artifact records each case, its exit status, and its transcript path.

## Publication boundary

The repository contains original host code and documentation only.
It excludes bootloader binaries, firmware images, device dumps, keys, and secrets.
The repository cites only the source image hash and relevant offsets.

No physical-device execution forms part of release validation.
