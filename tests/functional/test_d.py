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


class Test_d(unittest.FunctionalTestCase):

    def setUp(self):
        super().setUp()
        self.resetRegisters()

    def test_de(self):
        self.eq('one |two three', 'de', 'one | three')
        self.eq('one t|wo three', 'de', 'one t| three')
        self.assertRegister('"wo')
        self.assertRegister('-wo')
        self.assertRegisterIsNone('0')
        self.assertRegisterIsNone('1')

    def test_df(self):
        self.eq('one |two three', 'dft', 'one |hree')
        self.eq('one |two three three', 'd2ft', 'one |hree')
        self.eq('|a = 1', 'df=', '| 1')
        self.assertRegister('"a =')
        self.assertRegister('-a =')
        self.assertRegisterIsNone('0')
        self.assertRegisterIsNone('1')

    def test_dw(self):
        self.eq('one |two three', 'dw', 'one |three')
        self.eq('one t|wo three', 'dw', 'one t|three')
        self.assertRegister('"wo ')
        self.assertRegister('-wo ')
        self.assertRegisterIsNone('0')
        self.assertRegisterIsNone('1')

    def test_d__dollar(self):
        self.eq('one |two three', 'd$', 'one| ')
        self.eq('one t|wo three', 'd$', 'one |t')
        self.assertRegister('"wo three')
        self.assertRegister('-wo three')
        self.assertRegisterIsNone('0')
        self.assertRegisterIsNone('1')

    def test_dd(self):
        self.eq('one |two three', 'dd', '|')
        self.eq('one\n|two\nthree', 'dd', 'one\n|three')
        self.eq('one\ntwo|\nthree', 'dd', 'one\n|three')
        self.assertRegister('"two\n', linewise=True)
        self.assertRegister('1two\n', linewise=True)
        self.assertRegister('2two\n', linewise=True)
        self.assertRegister('3one two three\n', linewise=True)
        self.assertRegisterIsNone('-')
        self.assertRegisterIsNone('0')

    def test_dd_puts_cursor_on_first_non_blank(self):
        self.eq('one\n|two\n    three', 'dd', 'one\n    |three')

    def test_dd_last_line(self):
        self.eq('1\n2\n|3', 'dd', '1\n|2')
        self.eq('1\n2\n3\n|', 'dd', '1\n2\n|3')
        self.eq('1\n2\n|3\n', 'dd', '1\n2\n|')

    def test_d_visual_line_sets_linewise_register(self):
        self.eq('x\n|abc\n|y', 'l_d', 'n_x\n|y')
        self.assertRegister('"abc\n', linewise=True)
        self.assertRegister('1abc\n', linewise=True)
        self.assertRegisterIsNone('-')
        self.assertRegisterIsNone('0')

    def test_l_d_puts_cursors_on_first_non_blank(self):
        self.eq('    x\n|    a\n    b\n|    y\n', 'l_d', 'n_    x\n    |y\n')
        self.assertRegister('"    a\n    b\n', linewise=True)
        self.assertRegister('1    a\n    b\n', linewise=True)
        self.assertRegisterIsNone('-')
        self.assertRegisterIsNone('0')
