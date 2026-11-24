"""Independent acceptance tests, authored before model outputs are read."""
import importlib.util, math, os, pathlib, unittest
p=pathlib.Path(os.environ['CANDIDATE'])/'motion.py'
spec=importlib.util.spec_from_file_location('candidate_motion',p)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
MotionTracker=m.MotionTracker

class Acceptance(unittest.TestCase):
    def pair(self, actual, expected):
        self.assertEqual(len(actual),2)
        for a,e in zip(actual,expected): self.assertAlmostEqual(a,e,places=9)
    def test_01_first_baseline(self): self.pair(MotionTracker().update((100,200)),(0,0))
    def test_02_relative(self):
        t=MotionTracker(); t.update((10,20)); self.pair(t.update((13,16)),(3,-4))
    def test_03_stationary(self):
        t=MotionTracker(); t.update((3,4)); self.pair(t.update((3,4)),(0,0))
    def test_04_sensitivity(self):
        t=MotionTracker(sensitivity=2.5); t.update((0,0)); self.pair(t.update((2,-4)),(5,-10))
    def test_05_smoothing_initial(self):
        t=MotionTracker(smoothing=.25); t.update((0,0)); self.pair(t.update((8,-4)),(2,-1))
    def test_06_smoothing_recurrence(self):
        t=MotionTracker(smoothing=.5); t.update((0,0)); t.update((8,4)); self.pair(t.update((10,4)),(3,1))
    def test_07_loss_reacquisition(self):
        t=MotionTracker(); t.update((0,0)); t.update((4,4)); self.pair(t.update(None),(0,0)); self.pair(t.update((1000,1000)),(0,0)); self.pair(t.update((1002,999)),(2,-1))
    def test_08_loss_clears_smoothing(self):
        t=MotionTracker(smoothing=.5); t.update((0,0)); t.update((10,0)); t.update(None); t.update((40,0)); self.pair(t.update((42,0)),(1,0))
    def test_09_threshold_equal(self):
        t=MotionTracker(max_jump=5); t.update((0,0)); self.pair(t.update((3,4)),(3,4))
    def test_10_euclidean_jump(self):
        t=MotionTracker(max_jump=5); t.update((0,0)); self.pair(t.update((4,4)),(0,0)); self.pair(t.update((5,3)),(1,-1))
    def test_11_jump_before_sensitivity(self):
        t=MotionTracker(max_jump=5,sensitivity=100); t.update((0,0)); self.pair(t.update((3,4)),(300,400))
    def test_12_jump_clears_filter(self):
        t=MotionTracker(max_jump=10,smoothing=.5); t.update((0,0)); t.update((4,0)); t.update((100,0)); self.pair(t.update((102,0)),(1,0))
    def test_13_pause(self):
        t=MotionTracker(); t.update((0,0)); t.pause(); self.pair(t.update((20,20)),(0,0)); self.pair(t.update((21,20)),(0,0))
    def test_14_resume_rebase(self):
        t=MotionTracker(); t.update((0,0)); t.pause(); t.update((100,0)); t.resume(); self.pair(t.update((200,0)),(0,0)); self.pair(t.update((201,0)),(1,0))
    def test_15_resume_clears_even_if_active(self):
        t=MotionTracker(); t.update((0,0)); t.resume(); self.pair(t.update((1,0)),(0,0))
    def test_16_reset(self):
        t=MotionTracker(smoothing=.5); t.update((0,0)); t.update((4,0)); t.reset(); self.pair(t.update((50,50)),(0,0)); self.pair(t.update((52,50)),(1,0))
    def test_17_reset_preserves_pause(self):
        t=MotionTracker(); t.pause(); t.reset(); self.pair(t.update((1,1)),(0,0)); self.pair(t.update((2,2)),(0,0)); t.resume(); self.pair(t.update((3,3)),(0,0))
    def test_18_idempotent_pause(self):
        t=MotionTracker(); t.pause(); t.pause(); t.resume(); t.resume(); t.update((1,1)); self.pair(t.update((2,3)),(1,2))
    def test_19_config_sensitivity(self):
        for x in [0,-1,True,False,None,'2',float('inf'),float('-inf'),float('nan'),1j,[]]:
            with self.subTest(x=repr(x)),self.assertRaises(ValueError): MotionTracker(sensitivity=x)
    def test_20_config_smoothing(self):
        for x in [0,-.1,1.01,True,None,'0.5',float('inf'),float('nan'),1j]:
            with self.subTest(x=repr(x)),self.assertRaises(ValueError): MotionTracker(smoothing=x)
    def test_21_config_max_jump(self):
        for x in [0,-1,True,None,'5',float('inf'),float('nan'),1j]:
            with self.subTest(x=repr(x)),self.assertRaises(ValueError): MotionTracker(max_jump=x)
    def test_22_invalid_positions(self):
        for x in [3,'12',{},(1,),[1,2,3],(True,1),(1,False),(None,2),('1',2),(float('nan'),0),(0,float('inf')),(1j,2),iter([1,2])]:
            with self.subTest(x=repr(x)),self.assertRaises(ValueError): MotionTracker().update(x)
    def test_23_invalid_preserves_baseline_and_filter(self):
        for x in [(100,float('nan')),(True,0),(20,),None if False else 'bad']:
            t=MotionTracker(smoothing=.5); t.update((0,0)); t.update((4,0))
            with self.assertRaises(ValueError): t.update(x)
            self.pair(t.update((6,0)),(2,0))
    def test_24_paused_still_validates(self):
        t=MotionTracker(); t.pause()
        with self.assertRaises(ValueError): t.update((float('nan'),0))
    def test_25_list_float_coordinates(self):
        t=MotionTracker(); t.update([.1,.2]); self.pair(t.update([.4,-.3]),(.3,-.5))
    def test_26_instances_independent(self):
        a=MotionTracker(); b=MotionTracker(); a.update((10,10)); b.update((40,40)); self.pair(a.update((11,12)),(1,2)); self.pair(b.update((43,44)),(3,4))
    def test_27_repeated_none(self):
        t=MotionTracker(); self.pair(t.update(None),(0,0)); self.pair(t.update(None),(0,0)); self.pair(t.update((1,1)),(0,0))
    def test_28_negative_coordinates(self):
        t=MotionTracker(); t.update((-20,-30)); self.pair(t.update((-25,-28)),(-5,2))
    def test_29_stationary_filter_decay(self):
        t=MotionTracker(smoothing=.5); t.update((0,0)); t.update((8,0)); self.pair(t.update((8,0)),(2,0)); self.pair(t.update((8,0)),(1,0))
    def test_30_mutable_input_not_retained(self):
        t=MotionTracker(); pos=[1,2]; t.update(pos); pos[0]=50; self.pair(t.update((3,4)),(2,2))

if __name__=='__main__': unittest.main(verbosity=2)
