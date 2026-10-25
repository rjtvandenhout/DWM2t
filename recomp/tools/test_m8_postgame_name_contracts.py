"""Regression for the original five-glyph nickname codec on NPC breeding eggs."""
import unittest

from test_m8_story_checkpoints import verify_name_bytes


class OriginalNicknameContracts(unittest.TestCase):
    def setUp(self):
        self.saved = bytes(10)
        self.fresh = bytes(5)+bytes([0xF0])*5
        self.pins = [dict(record=17, offset=i, before=0, after=0xF0) for i in range(6, 11)]

    def test_original_npc_egg_exact_padding(self):
        verify_name_bytes(self.saved, self.fresh, 17, self.pins)

    def test_unpinned_change_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_name_bytes(self.saved, self.fresh, 17, [])

    def test_unlisted_name_glyph_change_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_name_bytes(self.saved, bytes([1])+self.fresh[1:], 17, self.pins)

    def test_wrong_or_duplicate_pin_is_rejected(self):
        for pins in (self.pins+[self.pins[0]], self.pins[:-1],
                     [dict(record=17, offset=6, before=1, after=0xF0), *self.pins[1:]]):
            with self.subTest(pins=pins), self.assertRaises(ValueError):
                verify_name_bytes(self.saved, self.fresh, 17, pins)

    def test_owner_or_other_record_pin_does_not_allow_nickname_change(self):
        for pins in ([dict(record=17, offset=21, before=0, after=0xF0)],
                     [dict(record=18, offset=i, before=0, after=0xF0) for i in range(6, 11)]):
            with self.subTest(pins=pins), self.assertRaises(ValueError):
                verify_name_bytes(self.saved, self.fresh, 17, pins)

    def test_historical_terminated_names_keep_their_original_check(self):
        verify_name_bytes(b'abc\xf0'+bytes(6), b'abc\xf0'+bytes([0xF0])*6, 1, [])
        with self.assertRaises(ValueError):
            verify_name_bytes(b'abc\xf0'+bytes(6), b'abd\xf0'+bytes(6), 1, [])


if __name__ == '__main__':
    unittest.main()
