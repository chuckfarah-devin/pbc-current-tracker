import cv2,json,numpy as np
from pathlib import Path
import argparse
a=argparse.ArgumentParser();a.add_argument('--output',type=Path,default=Path('motion_output'));args=a.parse_args()
p=args.output;p.mkdir(parents=True,exist_ok=True)
c=cv2.VideoCapture(str(Path(__file__).parent/'fixtures/delray-northward-example1.mp4'))
regions={'Left of reflection':(180,310,340,355),'Reflection edge':(370,315,490,355),'Right of reflection':(670,298,790,320)}
frames=[]
while True:
 ok,f=c.read()
 if not ok:break
 if int(c.get(cv2.CAP_PROP_POS_FRAMES))%6==1:frames.append(f)
rows={k:[] for k in regions}
for a,b in zip(frames,frames[1:]):
 for name,(x,y,r,t) in regions.items():
  aa=cv2.cvtColor(a[y:t,x:r],cv2.COLOR_BGR2GRAY);bb=cv2.cvtColor(b[y:t,x:r],cv2.COLOR_BGR2GRAY)
  flow=cv2.calcOpticalFlowFarneback(aa,bb,None,.5,3,15,3,5,1.2,0)
  rows[name].append([float(np.median(flow[:,:,0])),float(np.median(flow[:,:,1]))])
result={}
for name,v in rows.items():
 arr=np.array(v);result[name]={'median_dx_pixels_per_0_2s':round(float(np.median(arr[:,0])),3),'median_dy_pixels_per_0_2s':round(float(np.median(arr[:,1])),3),'leftward_pair_percent':round(float((arr[:,0]<0).mean()*100),1),'pair_count':len(v)}
f=frames[0].copy()
for name,(x,y,r,t) in regions.items():
 cv2.rectangle(f,(x,y),(r,t),(0,255,255),2);cv2.putText(f,name,(x,y-7),cv2.FONT_HERSHEY_SIMPLEX,.4,(0,255,255),1)
cv2.imwrite(str(p/'regions.jpg'),f)
(p/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
