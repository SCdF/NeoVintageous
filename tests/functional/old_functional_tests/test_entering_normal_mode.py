# Copyright (C) 2018 The NeoVintageous Team (NeoVintageous).
#
# This file is part of NeoVintageous.
#
# NeoVintageous is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# NeoVintageous is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NeoVintageous.  If not, see <https://www.gnu.org/licenses/>.

from NeoVintageous.tests import unittest

from NeoVintageous.nv.state import State


class TestViEnterNormalModeSingleSelectionLeftRoRight(unittest.ViewTestCase):

    def test_caret_ends_in_expected_region(self):
        self.write('foo bar\nfoo bar\nfoo bar\n')
        self.select((8, 11))
        State(self.view).mode = unittest.VISUAL

        self.view.run_command('_enter_normal_mode', {'mode': unittest.VISUAL})

        self.assertSelection(10)


class TestViEnterNormalModeSingleSelectionRightToLeft(unittest.ViewTestCase):

    def test_caret_ends_in_expected_region(self):
        self.write('foo bar\nfoo bar\nfoo bar\n')
        self.select((11, 8))
        self.state.mode = unittest.VISUAL

        self.view.run_command('_enter_normal_mode', {'mode': unittest.VISUAL})

        self.assertSelection(8)


class TestViEnterNormalModeMulipleSelectionsFromSelectMode(unittest.ViewTestCase):

    def test_carets_end_in_expected_region(self):
        self.write('foo bar\nfoo bar\nfoo bar\n')
        self.select([(8, 11), (16, 19)])
        State(self.view).mode = unittest.SELECT

        self.view.run_command('_enter_normal_mode', {'mode': unittest.SELECT})

        self.assertSelection([self.Region(8), self.Region(16)])


class TestViEnterNormalModeMulipleSelectionsFromNormalMode(unittest.ViewTestCase):

    def test_caret_ends_in_expected_region(self):
        self.write('foo bar\nfoo bar\nfoo bar\n')
        self.select([8, 16])
        State(self.view).mode = unittest.NORMAL

        self.view.run_command('_enter_normal_mode', {'mode': unittest.NORMAL})

        self.assertSelection(8)


class TestVisualBlock(unittest.ViewTestCase):

    def test_enter_normal_from_visual_block(self):
        self.write('1111\n2222\n')
        self.select([(1, 3), (6, 8)])

        State(self.view).mode = unittest.VISUAL_BLOCK

        self.view.run_command('_enter_normal_mode', {'mode': unittest.VISUAL_BLOCK})

        self.assertNormalMode()
        self.assertSelection(7)


class TestEnterNormalMode(unittest.ViewTestCase):

    def test_visual_mode_positions_cursor_on_last_character_not_eol_char(self):
        self.write('ab\n')
        self.select((1, 3))
        State(self.view).mode = unittest.VISUAL

        self.view.run_command('_enter_normal_mode', {'mode': unittest.VISUAL})

        self.assertNormalMode()
        self.assertSelection(1)

        self.write('ab\n')
        self.select((3, 1))
        State(self.view).mode = unittest.VISUAL

        self.view.run_command('_enter_normal_mode', {'mode': unittest.VISUAL})

        self.assertNormalMode()
        self.assertSelection(1)

        self.write('abc\ndef\n')
        self.select((1, 4))
        State(self.view).mode = unittest.VISUAL

        self.view.run_command('_enter_normal_mode', {'mode': unittest.VISUAL})

        self.assertNormalMode()
        self.assertSelection(2)

        self.write('abc\ndef\n')
        self.select((6, 3))
        State(self.view).mode = unittest.VISUAL

        self.view.run_command('_enter_normal_mode', {'mode': unittest.VISUAL})

        self.assertNormalMode()
        self.assertSelection(2)
