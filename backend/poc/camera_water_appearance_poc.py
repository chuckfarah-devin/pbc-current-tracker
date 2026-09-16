"""Measure visible water colour in reviewed camera regions, not underwater visibility.
python camera_water_appearance_poc.py --input camera-health-example --output water-appearance-example
Input is the image directory and result.json from beach_camera_health_poc.py.
Regions require visual review after a camera moves. No network calls.
"""
import argparse, json, hashlib
from pathlib import Path
from html import escape
import cv2
import numpy as np
from PIL import Image, ImageDraw

# Normalized regions selected on the actual September 14 camera views.
REGIONS = {
 'delray': [('Nearshore', (.65,.64,.96,.70)), ('Farther out', (.65,.39,.96,.49))],
 'lake_worth_s16': [('Nearshore', (.65,.75,.93,.88)), ('Farther out', (.12,.52,.40,.63))],
}

def measure(rgb):
    hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
    h,s,v=[hsv[:,:,i] for i in range(3)]
    # Exploratory colour bins, not calibrated water-quality thresholds.
    warm=(h<=30)&(s>=35)&(v>=40)
    blue=(h>=70)&(h<=130)&(s>=25)&(v>=40)
    other=~(warm|blue)
    return {'warm_percent':round(float(warm.mean()*100),1),
            'blue_green_percent':round(float(blue.mean()*100),1),
            'other_percent':round(float(other.mean()*100),1),
            'mean_rgb':[round(float(x),1) for x in rgb.mean(axis=(0,1))],
            'pixels':int(h.size)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('water-appearance-example'))
    a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
    metadata=a.input/'result.json'
    if not metadata.exists(): p.error(f'Missing {metadata}. Use the exact health output folder, usually camera_health_output (underscores).')
    sources=json.loads(metadata.read_text(encoding='utf-8'))
    cards=[]; results=[]
    for source in sources['cameras']:
        id_=source['id']
        if id_ not in REGIONS or not source.get('image_file'): continue
        im=Image.open(a.input/source['image_file']).convert('RGB')
        # Verify exact decoded image identity against provenance metadata.
        digest=hashlib.sha256(im.tobytes()).hexdigest()
        if digest!=source.get('pixel_hash'): raise ValueError('Image does not match source metadata: '+id_)
        preview=im.copy(); preview.thumbnail((1200,800)); d=ImageDraw.Draw(preview)
        rows=[]; samples=[]
        for label,region in REGIONS[id_]:
            x1,y1,x2,y2=region
            crop=im.crop((round(x1*im.width),round(y1*im.height),round(x2*im.width),round(y2*im.height)))
            m=measure(np.asarray(crop)); samples.append(dict(region=label,bounds=region,**m))
            box=(int(x1*preview.width),int(y1*preview.height),int(x2*preview.width),int(y2*preview.height))
            d.rectangle(box,outline='#ffe09a',width=3); d.text((box[0]+4,box[1]+4),label,fill='#ffffff',stroke_width=2,stroke_fill='#102e40')
            rows.append(f'<tr><td>{label}</td><td>{m["blue_green_percent"]}%</td><td>{m["warm_percent"]}%</td><td>{m["other_percent"]}%</td></tr>')
        preview.save(a.output/(id_+'.jpg'),quality=92)
        near=samples[0]
        headline='Predominantly blue / green' if near['blue_green_percent']>=60 else 'Warm-coloured water patch' if near['warm_percent']>=20 else 'Mixed / muted water colour'
        stamp=source.get('provider_label') or ('Stream retrieved '+source['checked_at']+'; capture time unverified')
        results.append({'camera':id_,'location':source['location'],'source_url':source.get('image_url',source['page_url']), 'timestamp':stamp,'pixel_hash':digest,'headline':headline,'samples':samples,'current_direction':None,'underwater_visibility':None})
        cards.append(f'''<article><div class="eyebrow">{escape(source['location'])} · camera observation</div><h2>{headline}</h2><p class="time">{escape(stamp)}</p><img src="{id_}.jpg" alt="Actual camera image with sampled water regions outlined"><p>Outlined areas are the only pixels measured. Blue/green appearance can support a visual check; it does not establish underwater visibility.</p><table><tr><th>Water sample</th><th>Blue/green</th><th>Warm/tan</th><th>Other</th></tr>{''.join(rows)}</table><details><summary>How to interpret this</summary><p>Percentages describe image colours, not percent clear water or seaweed coverage. Other includes grey water, reflections, shadows and colours outside the bins. Warm tones can have several causes; this does not identify tannins, runoff or sargassum.</p><p>Fixed sample boxes must be reviewed if the camera pans. Lighting, exposure, depth and the seabed can alter colour.</p></details><a href="{escape(source['page_url'],quote=True)}">Open camera source ↗</a></article>''')
    if not results: raise ValueError('No supported camera images in input')
    (a.output/'result.json').write_text(json.dumps({'mode':'Recorded-image example; not current conditions','method':'Exploratory HSV colour bins in manually selected water-only rectangles','results':results},indent=2),encoding='utf-8')
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PBC • Water appearance</title><style>:root{color-scheme:dark}body{margin:0;background:#071f2d;color:#e9f6f6;font:16px/1.55 system-ui}main{max-width:1100px;margin:auto;padding:32px 22px}.eyebrow{color:#72dad1;font-size:13px;letter-spacing:1px;text-transform:uppercase}h1{font-size:36px;margin:8px 0}h2{font-size:25px;margin:8px 0}.intro{max-width:760px;color:#bad1db}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:22px}article{background:#123343;border:1px solid #285365;border-radius:24px;padding:22px}img{width:100%;border-radius:12px}.time{font-size:12px;color:#bad1db}table{width:100%;font-size:12px;border-collapse:collapse}td,th{text-align:left;padding:10px 3px;border-bottom:1px solid #386071}details{margin:18px 0;color:#bad1db}a{color:#7ce1d5}.note{padding:20px;background:#183c49;border-radius:16px;margin:24px 0}@media(max-width:400px){.grid{display:block}article{margin-bottom:20px;padding:16px}h1{font-size:29px}}</style><main><div class="eyebrow">PBC snorkel conditions · working PoC</div><h1>What does the water look like?</h1><p class="intro">Real camera images, visible sample areas and repeatable measurements. Images are from the supplied capture bundle. Read each source timestamp; fetching a page does not update its camera image.</p><div class="grid">'''+''.join(cards)+'''</div><div class="note"><strong>What this example tells us</strong><p>The tables summarize colour in the outlined water samples. These are separate locations, not substitute observations for one another. No calibrated visibility distance or current direction is claimed.</p><strong>Current direction is a separate experiment</strong><p>A single image cannot establish motion. A short clip can show waves or boat wakes moving without revealing the underlying current. Tracking a persistent drifting feature over time is the next validation step.</p></div><p class="time">Imagery: original camera sources linked above. Colour thresholds are exploratory and have not been calibrated against in-water observations.</p></main></html>'''
    (a.output/'card.html').write_text(html,encoding='utf-8')
    print(json.dumps(results,indent=2))

if __name__=='__main__': main()
