from app import calc
from django.test import SimpleTestCase


class CalcTests(SimpleTestCase):

    """ Test add two Number"""
    def test_add_number(self):
        res=calc.add(3,2)
        self.assertEqual(res,5)
