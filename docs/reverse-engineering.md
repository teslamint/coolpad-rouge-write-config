# Reverse-engineering note

Date: 2026-10-12

## Evidence boundary

This note describes one acquired Coolpad Rouge 3320A `aboot.img`.
Its SHA-256 value is:

```text
ade1127757a40588a449459353928ba0658cad658ad9e20bd2e04eb0984c5296
```

The ELF load segment maps file offset `0x8000` to address `0x8f600000`.
All addresses below use that mapping.

## Command registration

The string `write-config:` is at file offset `0x907dc`.
Its virtual address is `0x8f6887dc`.

The registration code starts at `0x8f62396c`.
It passes the string and handler `0x8f61c10c` to the fastboot dispatcher.
The dispatcher registration function is at `0x8f621fec`.

This path uses normal fastboot command framing.
The handler does not request a fastboot data phase.

## Handler behavior

The handler begins at `0x8f61c10c`.
It copies one suffix byte from the command argument.

The string `config` is at `0x8f65a080`.
The handler resolves this partition and obtains its offset and size.
It rejects a partition smaller than 512 bytes.

The handler calculates this address:

```text
partition_offset + partition_size - 512
```

The read call is at `0x8f61c1f0`.
It reads 512 bytes into a local buffer.

The instructions from `0x8f61c1fc` through `0x8f61c220` inspect the suffix.
They write the normalized value to buffer byte 511.

- ASCII `1` becomes `0x01`.
- Every other suffix becomes `0x00`.

The host client accepts only ASCII `0` and ASCII `1`.

The write call is at `0x8f61c24c`.
It writes the complete 512-byte buffer to the same address.

## Response

The response format string is at `0x8f65a0d4`:

```text
sz:%d, arg:%d, tag:%d
```

The successful path reaches the fastboot `OKAY` function at `0x8f61c278`.
The observed 512 KiB partition yields `sz:524288, arg:0`.
The tag is the decimal ASCII code for the suffix.
It is not a readback of the stored byte.
`OKAY` means only that the storage helper returned zero.

Known failure strings include these values:

- `partition table doesn't exist`
- `partition size error`
- `flash read failure`
- `flash write failure`

## Unknown semantic meaning

The handler proves the storage location and byte transformation.
It does not name the feature that consumes the stored byte.

The handler calls the byte a `tag` in its response.
That label does not prove an unlock, repair, or provisioning function.

No consumer is established by this bounded analysis.
This statement does not prove that no consumer exists elsewhere in the firmware.
