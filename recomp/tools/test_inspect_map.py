"""Original map assets and LR35902 decompression boundary regressions."""
import hashlib
import unittest
from unittest.mock import patch

import inspect_map


class OriginalMapDecompressionTests(unittest.TestCase):
    def decode_fixture(self, encoded):
        # Compressed-byte fixture only: never executed or loaded as game state.
        with patch.dict(inspect_map.BANKS, {254: bytes.fromhex(encoded)}):
            return inspect_map.decompress(254, 0x4000)

    def test_dictionary_run_wraps_per_byte(self):
        self.assertEqual(
            self.decode_fixture('06 00 FE 40 FE FF F1'),
            bytes.fromhex('40 00 40 00 40 00'))

    def test_extended_counter_wraps_before_copying(self):
        self.assertEqual(
            self.decode_fixture('05 00 FE 40 FE 00 0F EE 41 42 43'),
            bytes.fromhex('40 40 41 42 43'))

    def test_extended_zero_counter_copies_256_bytes(self):
        self.assertEqual(
            self.decode_fixture('01 01 FE 40 FE 00 0F ED'),
            bytes([0x40])*257)

    def test_original_random_world_assets(self):
        # Source bank/addresses from original97:$5443 and map66. Two surface
        # baselines match native captures apart from original structure overlays;
        # the shrine matches all360 captured bytes. See postgame raw evidence.
        assets = [
            (101, 0x6F78, 'b065011f3a6afc28ec0821bd1ffd2f18ae8356ff78cc73a04b268f021be32f57'),
            (102, 0x4EFF, '80dec5f26646f06d83720a80e1671b439f2ec20ac0efbeb7f1a41f7beb644c45'),
            (144, 0x4F44, '549330e7f092d88c6564807bbdd107347e4d1ff5ff7d9f8a47f63488a596ef2b'),
        ]
        for number, address, digest in assets:
            with self.subTest(bank=number, address=hex(address)):
                decoded = inspect_map.decompress(number, address)
                self.assertEqual(len(decoded), 360)
                self.assertEqual(hashlib.sha256(decoded).hexdigest(), digest)


if __name__ == '__main__':
    unittest.main()
