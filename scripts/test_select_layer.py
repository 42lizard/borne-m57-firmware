#!/usr/bin/env python3
"""Exercise the host helper at the HIDAPI boundary, without a keyboard."""
import unittest
from unittest.mock import Mock

from select_layer import select_layer


class SelectLayerTests(unittest.TestCase):
    def setUp(self):
        self.hid = Mock()
        self.hid.enumerate.return_value = [
            dict(path=b'keyboard', usage_page=1, usage=6),
            dict(path=b'raw', usage_page=0xFF60, usage=0x61, serial_number='m57'),
        ]
        self.device = self.hid.device.return_value
        self.device.write.return_value = 33
        self.device.read.return_value = bytes([0x40, 0, 3]) + bytes(29)

    def test_selects_raw_interface_and_uses_unnumbered_report(self):
        select_layer(self.hid, 3)
        self.hid.enumerate.assert_called_once_with(0x6401, 0x45D4)
        self.device.open_path.assert_called_once_with(b'raw')
        self.device.write.assert_called_once_with(bytes([0, 0x40, 1, 3]) + bytes(29))
        self.device.read.assert_called_once_with(32, 1000)
        self.device.close.assert_called_once()

    def test_returns_to_layer_zero(self):
        self.device.read.return_value = bytes([0x40, 0, 0]) + bytes(29)
        select_layer(self.hid, 0)
        self.device.write.assert_called_once_with(bytes([0, 0x40, 1, 0]) + bytes(29))

    def test_rejects_missing_or_ambiguous_interface(self):
        raw = self.hid.enumerate.return_value[1]
        for devices in ([], [raw, dict(raw, path=b'other', serial_number='other')]):
            self.hid.enumerate.return_value = devices
            with self.assertRaisesRegex(RuntimeError, 'Expected one'):
                select_layer(self.hid, 3)
        self.hid.device.assert_not_called()

    def test_serial_selects_one_keyboard(self):
        raw = self.hid.enumerate.return_value[1]
        self.hid.enumerate.return_value.append(dict(raw, path=b'other', serial_number='other'))
        select_layer(self.hid, 3, serial='m57')
        self.device.open_path.assert_called_once_with(b'raw')

    def test_reports_timeout_rejection_and_unexpected_replies(self):
        for reply, message in (
            ([], 'Timed out'),
            ([0x40], 'Unexpected'),
            (bytes([0xFF]) + bytes(31), 'Unexpected'),
            (bytes([0x40, 0, 4]) + bytes(29), 'Unexpected'),
            (bytes([0x40, 1, 3]) + bytes(29), 'malformed'),
            (bytes([0x40, 2, 3]) + bytes(29), 'outside configured range'),
            (bytes([0x40, 7, 3]) + bytes(29), 'unknown status'),
        ):
            with self.subTest(message=message):
                self.device.read.return_value = reply
                with self.assertRaisesRegex(RuntimeError, message):
                    select_layer(self.hid, 3)
                self.device.close.assert_called()

    def test_reports_device_access_and_write_failures(self):
        self.device.open_path.side_effect = OSError('permission denied')
        with self.assertRaisesRegex(OSError, 'permission denied'):
            select_layer(self.hid, 3)
        self.device.close.assert_called_once()
        self.device.open_path.side_effect = None
        self.device.write.return_value = 0
        with self.assertRaisesRegex(RuntimeError, 'Incomplete'):
            select_layer(self.hid, 3)


if __name__ == '__main__':
    unittest.main()
