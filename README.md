# Coolpad Rouge `write-config` client

This project sends the hidden `write-config:0` or `write-config:1` command.
It targets the Coolpad Rouge 3320A bootloader.

The command changes the final byte of the 512 KiB `config` partition.
The byte becomes `0x00` or `0x01`.

The higher-level meaning of this byte is unknown.
Do not describe this command as an unlock or repair command.

## Safety warning

This command writes to persistent storage.
A power loss or USB fault can leave the result unknown.

Create and verify a `config` partition backup before execution.
Use this tool only on a device that you own or may service.

The release tests use a simulated USB transport.
They never execute the command on a physical device.

## Requirements

- Python 3.11 or later
- PyUSB
- A working libusb backend
- A Coolpad Rouge 3320A in fastboot mode

## Install

The user creates a virtual environment in the repository.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install '.[usb]'
```

## Create a plan

Plan mode does not enumerate or open USB devices.

```sh
coolpad-rouge-write-config --serial SERIAL --value 1
```

The command prints a JSON plan.
Construct the acknowledgement token from the plan before execution.

## Execute the write

The user supplies the exact USB serial and acknowledgement token.

```sh
coolpad-rouge-write-config \
  --serial SERIAL \
  --value 1 \
  --execute \
  --acknowledge 'WRITE-CONFIG:3320A:SERIAL:1'
```

The client checks these values before the write:

1. The USB vendor identifier is `0x1ebf`.
2. The USB serial equals `--serial`.
3. `getvar:product` returns `3320A`.
4. `getvar:serialno` returns the same serial.

The client sends no firmware image and no data phase.
An accepted response does not read the stored byte back.
It does not prove that storage is durable.

## Test

The maintainer runs the end-to-end suite from the repository root.

```sh
python3 tools/run_e2e.py
```

The suite writes `.artifacts/e2e-results.json`.
It also writes one fake-transport transcript per execution case.

## Reverse-engineering basis

The analyzed bootloader registers `write-config:` with its fastboot dispatcher.
The handler reads the last 512-byte sector of the `config` partition.
It changes byte 511 and writes the sector back.

The analysis used this `aboot.img` SHA-256 value:

```text
ade1127757a40588a449459353928ba0658cad658ad9e20bd2e04eb0984c5296
```

The repository does not distribute that image or any firmware data.
See [the analysis note](docs/reverse-engineering.md) for offsets and limits.

The USB framing follows the
[Android fastboot protocol](https://android.googlesource.com/platform/system/core/+/refs/tags/android-cts-7.0_r33/fastboot/fastboot_protocol.txt).

## License

MIT
