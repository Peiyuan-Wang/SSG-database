import unittest
from sympy import Rational,sqrt,pi
from ssg_database.parameter_input import parse_parameters

class ParameterInputTests(unittest.TestCase):
    def test_exact_and_approximate_values(self):
        self.assertEqual(parse_parameters('1/7',1),((Rational(1,7),),False))
        self.assertEqual(parse_parameters('1/997',1),((Rational(1,997),),True))
        self.assertEqual(parse_parameters('sqrt(2)/10',1),((sqrt(2)/10,),True))
        self.assertEqual(parse_parameters('pi/10',1),((pi/10,),True))
        values,approx=parse_parameters('0.81',1)
        self.assertTrue(approx);self.assertAlmostEqual(float(values[0]),0.81)
        self.assertEqual(len(parse_parameters('1/3, sqrt(2)/5',2)[0]),2)

    def test_invalid_inputs_are_rejected(self):
        for text,n in [('1/0',1),('nan',1),('sqrt(-1)',1),('1/2,1/3',1),('__import__("os")',1),('10**999999',1),('',1)]:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):parse_parameters(text,n)
