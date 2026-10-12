"""Small PyUSB utility surface used by the production transport."""

ENDPOINT_IN = 0x80
ENDPOINT_OUT = 0x00
ENDPOINT_TYPE_BULK = 2


def endpoint_direction(address: int) -> int:
    return address & ENDPOINT_IN


def endpoint_type(attributes: int) -> int:
    return attributes & 0x03


def get_string(device, index: int) -> str:
    return device.serial


def claim_interface(device, interface_number: int) -> None:
    return None


def release_interface(device, interface_number: int) -> None:
    return None


def dispose_resources(device) -> None:
    return None
