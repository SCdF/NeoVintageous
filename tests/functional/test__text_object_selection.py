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


class TestObjectSelection(unittest.FunctionalTestCase):

    def test_v_at(self):
        self.eq('x<p>a|bc</p>x', 'v_at', 'x|<p>abc</p>|x')
        self.eq('x<p><b>_</b>a|bc<i>_</i>e</p>x', 'v_at', 'x|<p><b>_</b>abc<i>_</i>e</p>|x')

    def test_v_iw(self):
        self.eq('x    fi|zz    xx', 'v_iw', 'x    |fizz|    xx')
        self.eq('x  |  fizz    xx', 'v_iw', 'x|    |fizz    xx')
        self.eq('x    |fizz|    xx', 'v_iw', 'x    |fizz    |xx')
        self.eq('x|    fizz    xx', 'v_3iw', 'x|    fizz    |xx')
        self.eq('x    fi|zz    xx    yy    zz', 'v_3iw', 'x    |fizz    xx|    yy    zz')
        self.eq('x  .,|-;abc#"]  y', 'v_iw', 'x  |.,-;|abc#"]  y')
        self.eq('x  .,-;a|bc#"]  y', 'v_iw', 'x  .,-;|abc|#"]  y')

    def test_v_aw(self):
        self.eq('x    fi|zz    xx', 'v_aw', 'x    |fizz    |xx')
        self.eq('x    |fizz    xx', 'v_aw', 'x    |fizz    |xx')
        self.eq('x  |  f|izz    xx', 'v_aw', 'x  |  fizz    |xx')
        self.eq('x    fi|zz    xx    yy    zz', 'v_3aw', 'x    |fizz    xx    yy    |zz')

    def test_v_iW(self):
        self.eq('x  |.,-;abc#"]  y', 'v_iW', 'x  |.,-;abc#"]|  y')
        self.eq('x  .,|-;abc#"]  y', 'v_iW', 'x  |.,-;abc#"]|  y')

    def test_v_aW(self):
        self.eq('x    fi|zz    xx', 'v_aW', 'x    |fizz    |xx')
        self.eq('x    fi|zz    xx    yy    zz', 'v_3aW', 'x    |fizz    xx    yy    |zz')
        self.eq('.    |.,-   f.";   (x)    yy', 'v_aW', '.    |.,-   |f.";   (x)    yy')
        self.eq('.    .|,-   f.";   (x)    yy', 'v_aW', '.    |.,-   |f.";   (x)    yy')
        self.eq('.   |.,-   f.";   (x)    yy', 'v_3aW', '.   |.,-   f.";   (x)    |yy')

    def test_v_is(self):
        self.eq('x.  x   Fi|zz buzz.yy.  xx', 'v_is', 'x.  |x   Fizz buzz.yy.|  xx')
        self.eq('x.  x  Fi|zz buzz.  y', 'v_is', 'x.  |x  Fizz buzz.|  y')
        self.eq('x.  a |b c.  y', 'v_is', 'x.  |a b c.|  y')
        self.eq('x?  a |b c?  y', 'v_is', 'x?  |a b c?|  y')
        self.eq('x!  a |b c!  y', 'v_is', 'x!  |a b c!|  y')
        self.eq('x.  (a |b c).  y', 'v_is', 'x.  |(a b c).|  y')
        self.eq('x.  [a |b c].  y', 'v_is', 'x.  |[a b c].|  y')
        self.eq('x.  "a |b c".  y', 'v_is', 'x.  |"a b c".|  y')
        self.eq('x.  (["a |b c"]).  y', 'v_is', 'x.  |(["a b c"]).|  y')
        self.eq('x.\n\na\b|b\nc.\n\nx', 'v_is', 'x.\n\n|a\bb\nc.|\n\nx')

    def test_v_as(self):
        self.eq('x.  x  Fi|zz buzz.  y', 'v_as', 'x.  |x  Fizz buzz.|  y')

    def test_ip(self):
        self.eq('1\n\n2\n|3\n4\n\n\n5', 'v_ip', '1\n\n|2\n3\n4\n|\n\n5')
        self.eq('1\n\n2\n|3\n4\n\n\n5', 'v_2ip', '1\n\n|2\n3\n4\n\n\n|5')
        self.eq('1\n\n2\n|3\n4\n\n\n5\n6\n\n7', 'v_3ip', '1\n\n|2\n3\n4\n\n\n5\n6\n|\n7')

    def test_ap(self):
        self.eq('1\n\n2\n|3\n4\n\n\n5', 'v_ap', '1\n\n|2\n3\n4\n\n\n|5')
        self.eq('1\n\n2\n|3\n4\n\n\n5\n6\n\n7', 'v_2ap', '1\n\n|2\n3\n4\n\n\n5\n6\n\n|7')
        self.eq('x\n\n|1\n\n2\n3\n4\n\n\n5\n6\n\n7', 'v_3ap', 'x\n\n|1\n\n2\n3\n4\n\n\n5\n6\n\n|7')

    def test_i_bracket(self):
        for target in ('[', ']'):
            self.eq('[fi|zz]', 'v_i' + target, '[|fizz|]')

    def test_a_bracket(self):
        for target in ('[', ']'):
            self.eq('x[fi|zz]x', 'v_a' + target, 'x|[fizz]|x')
            self.eq('x[\nfi|zz\n]x', 'v_a' + target, 'x|[\nfizz\n]|x')
            self.eq('x[\n\n  \n    fi|zz\n\n\n]x', 'v_a' + target, 'x|[\n\n  \n    fizz\n\n\n]|x')

    def test_i_paren(self):
        for target in ('(', ')', 'b'):
            self.eq('(fi|zz)', 'v_i' + target, '(|fizz|)')

    def test_a_paren(self):
        for target in ('(', ')', 'b'):
            self.eq('x(fi|zz)x', 'v_a' + target, 'x|(fizz)|x')
            self.eq('x(\nfi|zz\n)x', 'v_a' + target, 'x|(\nfizz\n)|x')
            self.eq('x(\n\n  \n    fi|zz\n\n\n)x', 'v_a' + target, 'x|(\n\n  \n    fizz\n\n\n)|x')

    def test_i_square_bracket(self):
        for target in ('<', '>'):
            self.eq('<fi|zz>', 'v_i' + target, '<|fizz|>')

    def test_a_square_bracket(self):
        for target in ('<', '>'):
            self.eq('x<fi|zz>x', 'v_a' + target, 'x|<fizz>|x')
            self.eq('x<\nfi|zz\n>x', 'v_a' + target, 'x|<\nfizz\n>|x')
            self.eq('x<\n\n  \n    fi|zz\n\n\n>x', 'v_a' + target, 'x|<\n\n  \n    fizz\n\n\n>|x')

    def test_issue_161_at(self):
        self.eq(
            '<head>\n    <link rel=|"shortcut icon" href="favicon.png">\n</head>',
            'v_at',
            '|<head>\n    <link rel="shortcut icon" href="favicon.png">\n</head>|'
        )

    def test_v_it(self):
        self.eq('x<p>a|bc</p>x', 'v_it', 'x<p>|abc|</p>x')
        self.eq('x<p>_<i>_</i>a|bc<i>_</i>d</p>x', 'v_it', 'x<p>|_<i>_</i>abc<i>_</i>d|</p>x')

    def test_161(self):
        self.eq(
            '<head>\n    <link rel=|"shortcut icon" href="favicon.png">\n</head>',
            'v_it',
            '<head>|\n    <link rel="shortcut icon" href="favicon.png">\n|</head>'
        )

    def test_v_ibrace(self):
        self.eq('{\na\n|b\nc\n}\n', 'v_i{', '{\n|a\nb\nc\n|}\n')
        self.eq('{\na\n|b\nc\n}\n', 'v_i}', '{\n|a\nb\nc\n|}\n')
        self.eq('{xx\na\n|b\nc\nxx}\n', 'v_i}', '{|xx\na\nb\nc\nxx|}\n')
