"""
Test for helper functions

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

from unittest import TestCase

import src.lib.config as config
import src.lib.helpers as helpers


class HelpersTest(TestCase):

    def test_parse_record(self):
        r1_s = "(['5rLhPSFu', 'hardened steel', 'zJcgKqGI', 'end mill', 4], \
            [(261, 4, 3412, 6), (35, 28, 24276, 7)])"
        r1 = helpers.Record(('5rLhPSFu', 'hardened steel', 'zJcgKqGI'),
                            ('end mill', 4),
                            [(261, 4, 3412, 6), (35, 28, 24276, 7)])
        r2_s = "['tqExkPZC', 'non-ferrous metal', 'et7TNK8X', 'ball mill', 4], \
            [(40, 80, 1409, 3), (175, 274, 27695, 4)])\n"
        r2 = helpers.Record(('tqExkPZC', 'non-ferrous metal', 'et7TNK8X'),
                            ('ball mill', 4),
                            [(40, 80, 1409, 3), (175, 274, 27695, 4)])
        self.assertEqual(r1, helpers.parse_record(r1_s))
        self.assertEqual(r2, helpers.parse_record(r2_s))

    def test_generate_auth_header(self):
        self.assertEqual(helpers.generate_auth_header("user", "pwd"),
                         [('Authorization', 'Basic dXNlcjpwd2Q=')])

    def test_base64(self):
        x = 13
        self.assertEqual(x, helpers.from_base64(helpers.to_base64(x)))

    def test_print_time(self):
        t = 10.0 / 1000
        self.assertEqual(
            "10.0ms",
            helpers.print_time(t)
        )
        t = 5.555
        self.assertEqual(
            "5.55s",
            helpers.print_time(t)
        )
        t = 340.600
        self.assertEqual(
            "5min 40.6s",
            helpers.print_time(t)
        )
        t = 8113.000
        self.assertEqual(
            "2h 15min 13.0s",
            helpers.print_time(t)
        )

    def test_get_temp_file(self):
        tmp = helpers.get_temp_file()
        self.assertIn(
            config.TEMP_DIR,
            tmp
        )
