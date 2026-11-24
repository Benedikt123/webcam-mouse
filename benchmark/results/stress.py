import importlib.util,json,math,pathlib,sys,time
p=pathlib.Path(sys.argv[1])/'motion.py'; s=importlib.util.spec_from_file_location('motion',p); m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
t=m.MotionTracker(smoothing=.3,max_jump=100); times=[]
if '--integer-baseline' in sys.argv: t.update((0,0))
for batch in range(6):
 start=time.perf_counter()
 for i in range(batch*400,(batch+1)*400): t.update((100*math.sin(i*.01),100*math.cos(i*.01)))
 times.append(time.perf_counter()-start)
print(json.dumps({'updates':2400,'batch_size':400,'batch_seconds':times,'total_seconds':sum(times),'last_over_first':times[-1]/times[0]}))
