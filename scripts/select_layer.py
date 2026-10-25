#!/usr/bin/env python3
"""Select a BORNE m57 runtime layer over its existing VIA Raw HID interface."""
import argparse

VID = 0x6401
PID = 0x45D4
USAGE_PAGE = 0xFF60
USAGE = 0x61
REPORT_SIZE = 32


def select_layer(hid, layer, serial=None):
    devices = [device for device in hid.enumerate(VID, PID)
               if device.get('usage_page') == USAGE_PAGE
               and device.get('usage') == USAGE
               and (serial is None or device.get('serial_number') == serial)]
    if len(devices) != 1:
        raise RuntimeError(f'Expected one matching Raw HID interface, found {len(devices)}; '
                           'connect one keyboard or use --serial')
    request = bytes([0x40, 1, layer]) + bytes(29)
    device = hid.device()
    try:
        device.open_path(devices[0]['path'])
        # HIDAPI writes require a leading report ID, even for unnumbered reports.
        if device.write(b'\x00' + request) != REPORT_SIZE + 1:
            raise RuntimeError('Incomplete HID write')
        # HIDAPI reads omit the report ID for this unnumbered interface.
        reply = bytes(device.read(REPORT_SIZE, 1000))
        if not reply:
            raise RuntimeError('Timed out waiting for firmware reply')
        if len(reply) != REPORT_SIZE or reply[0] != 0x40 or reply[2:] != request[2:]:
            raise RuntimeError(f'Unexpected firmware reply: {reply.hex(" ")}')
        if reply[1] != 0:
            reason = {1: 'malformed request', 2: 'layer outside configured range'}.get(
                reply[1], f'unknown status {reply[1]}')
            raise RuntimeError(f'Firmware rejected request: {reason}')
    finally:
        device.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('layer', type=int, help='zero-based layer index (0–9 in this build)')
    parser.add_argument('--serial', help='select a keyboard by its HID serial number')
    args = parser.parse_args()
    if not 0 <= args.layer <= 255:
        parser.error('layer must fit in one byte (0–255); firmware validates its configured range')
    try:
        import hid
        select_layer(hid, args.layer, args.serial)
    except ImportError:
        parser.exit(1, 'Install the hidapi Python package: python3 -m pip install hidapi\n')
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(1, f'Layer selection failed: {error}\n')
    print(f'Selected layer {args.layer}')


if __name__ == '__main__':
    main()
