"""Deterministic state-machine replay against a simple float reference."""
import importlib.util,json,os,pathlib,random,unittest
p=pathlib.Path(os.environ['CANDIDATE'])/'motion.py';s=importlib.util.spec_from_file_location('replay_motion',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Replay(unittest.TestCase):
 def test_seeded_state_machine(self):
  for seed in range(20):
   rng=random.Random(seed);a=.3;gain=1.7;limit=5.;t=m.MotionTracker(sensitivity=gain,smoothing=a,max_jump=limit);baseline=None;old=(0.,0.);paused=False;x=y=0.
   for step in range(500):
    kind=rng.randrange(12)
    if kind in (0,1,2):
     op=('pause','resume','reset')[kind];getattr(t,op)();baseline=None;old=(0.,0.)
     if op=='pause':paused=True
     if op=='resume':paused=False
     continue
    if kind==3:
     self.assertEqual(t.update(None),(0,0));baseline=None;old=(0.,0.);continue
    if kind==4:
     with self.assertRaises(ValueError):t.update((float('nan'),0))
     continue
    x+=rng.uniform(-3,3);y+=rng.uniform(-3,3)
    if kind==5:x+=50
    pos=(int(x),int(y)) if kind==6 else (x,y)
    if paused:expected=(0.,0.)
    elif baseline is None:baseline=pos;expected=(0.,0.)
    else:
     dx,dy=pos[0]-baseline[0],pos[1]-baseline[1];baseline=pos
     if dx*dx+dy*dy>limit*limit:old=(0.,0.)
     else:old=(a*gain*dx+(1-a)*old[0],a*gain*dy+(1-a)*old[1])
     expected=old
    out=t.update(pos)
    for axis in (0,1):self.assertAlmostEqual(float(out[axis]),expected[axis],delta=1e-9,msg=f'seed={seed} step={step} axis={axis}')
if __name__=='__main__':unittest.main(verbosity=2)
