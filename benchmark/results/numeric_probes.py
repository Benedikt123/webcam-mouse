"""Supplementary numerical probes: extreme inputs, not camera acceptance gates."""
import importlib.util,os,pathlib,unittest
from fractions import Fraction
p=pathlib.Path(os.environ['CANDIDATE'])/'motion.py';s=importlib.util.spec_from_file_location('probe_motion',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class NumericProbes(unittest.TestCase):
 def test_huge_integer_configuration_and_small_motion(self):
  t=m.MotionTracker(max_jump=10**400);t.update((10**400,0));self.assertEqual(t.update((10**400+1,0)),(1,0))
 def test_huge_rational_configuration(self):
  t=m.MotionTracker(max_jump=Fraction(10**400,3));self.assertEqual(t.update((0,0)),(0,0))
 def test_large_mixed_coordinate_small_motion(self):
  origin=2**60;t=m.MotionTracker();t.update((float(origin),0));self.assertEqual(t.update((origin+1,0)),(1,0))
 def test_fraction_diagonal_equal_threshold(self):
  t=m.MotionTracker(max_jump=Fraction(1,10));t.update((0,0));out=t.update((Fraction(3,50),Fraction(2,25)));self.assertAlmostEqual(float(out[0]),.06,places=12);self.assertAlmostEqual(float(out[1]),.08,places=12)
 def test_finite_gain_with_overflowing_intermediate(self):
  t=m.MotionTracker(sensitivity=1e308,smoothing=.25);t.update((0,0));out=t.update((4,0));self.assertEqual(float(out[0]),1e308)
 def test_tiny_perpendicular_displacement_over_threshold(self):
  t=m.MotionTracker(max_jump=1.0);t.update((0.0,0.0));self.assertEqual(t.update((1.0,1e-12)),(0,0))
if __name__=='__main__':unittest.main(verbosity=2)
