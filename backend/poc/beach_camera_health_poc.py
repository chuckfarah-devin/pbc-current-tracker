"""Three-camera source health experiment. No current/clarity inference.
Run once; rerun in the same output folder to compare frames across checks.
Requires requests Pillow numpy opencv-python tzdata.
"""
import argparse
from datetime import datetime, timezone
from html import escape
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo
import numpy as np
from PIL import Image
import requests

# Use platform certificate trust where available; never disable TLS verification.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

SITES = {
 'boynton': {'name':'Boynton Inlet','url':'https://video-monitoring.com/beachcams/boyntoninlet/',
             'views':{'s6':'South view','s10':'North view','s8':'East view','s4':'West view'}},
 'lake_worth': {'name':'Lake Worth Inlet','url':'https://video-monitoring.com/beachcams/lakeworthinlet/',
                'views':{'s4':'North shore','s6':'North shore zoom','s8':'Inlet shot','s12':'Inlet zoom','s16':'North east view'}}}
DELRAY='https://streamer5.brownrice.com/delraybeach1/delraybeach1.stream/main_playlist.m3u8'
ALLOWED={'video-monitoring.com','streamer5.brownrice.com'}


def utcnow(): return datetime.now(timezone.utc)


def get(url):
    if urlparse(url).hostname not in ALLOWED: raise ValueError('Unexpected source host: '+url)
    r=requests.get(url,timeout=(8,20),headers={'Cache-Control':'no-cache'})
    r.raise_for_status()
    if len(r.content)>20_000_000: raise ValueError('Response exceeds POC size limit')
    return r


def freshness(timestamp, now, max_age):
    try:
        if isinstance(timestamp,bool): raise ValueError()
        captured=datetime.fromtimestamp(float(timestamp),timezone.utc)
        age=(now-captured).total_seconds()/60
    except (TypeError,ValueError,OverflowError,OSError):
        return {'freshness':'unknown','capture_utc':None,'age_minutes':None}
    status='future_timestamp' if age < -5 else 'fresh' if age <= max_age else 'stale'
    return {'freshness':status,'capture_utc':captured.isoformat(),'age_minutes':round(age,1)}


def inspect_frame(raw, path, previous):
    im=Image.open(BytesIO(raw)).convert('RGB')
    if min(im.size)<100: raise ValueError('Image too small for camera review')
    rgb=np.asarray(im)
    digest=hashlib.sha256(im.tobytes()).hexdigest()
    gray=np.asarray(im.convert('L'))
    flags=[]
    if gray.mean()<25: flags.append('dark frame: night/exposure/obstruction possible')
    if gray.std()<8: flags.append('low-detail frame: blank/obstructed screen possible')
    same=bool(previous and previous.get('pixel_hash')==digest)
    if same: flags.append('identical decoded pixels since previous run; not proof of a frozen camera')
    im.save(path)
    return {'image_file':path.name,'pixel_hash':digest,'width':im.width,'height':im.height,
            'mean_brightness':round(float(gray.mean()),1),'visual_flags':flags,
            'identical_to_previous':same,'previous_checked_at':previous.get('checked_at') if previous else None,
            'visual_review':'Required: maintenance text, fog, glare, camera pan and usable ocean area are not reliably classified automatically.'}


def county(site_id, output, previous, max_age):
    site=SITES[site_id]; results=[]
    try:
        page=get(site['url']).text
        # Strip scripts: avoid treating JavaScript keywords as maintenance notices.
        plain=re.sub(r'<script\b.*?</script>','',page,flags=re.S|re.I)
        notice=bool(re.search(r'under maintenance|camera unavailable|temporarily offline',plain,re.I))
        data=get(urljoin(site['url'],'latest.json')).json()
        if not isinstance(data,dict): raise ValueError('Unexpected latest.json schema')
    except Exception as exc:
        return [{'id':site_id,'location':site['name'],'view':'All views','page_url':site['url'],
                 'status':'unavailable','error':str(exc),'checked_at':utcnow().isoformat()}]
    for key,label in site['views'].items():
        id_=site_id+'_'+key; now=utcnow()
        result={'id':id_,'location':site['name'],'view':label,'page_url':site['url'],
                'checked_at':now.isoformat(),'page_maintenance_notice':notice}
        try:
            item=data.get(key)
            if not isinstance(item,dict): raise ValueError('View missing from latest manifest')
            result.update(freshness(item.get('timestamp'),now,max_age))
            result['capture_time_basis']='provider latest.json timestamp (not HTTP retrieval time)'
            result['provider_label']=item.get('timedate')
            url=urljoin(site['url'],item['hr']); result['image_url']=url
            raw=get(url).content
            result.update(inspect_frame(raw,output/(id_+'.png'),previous.get(id_)))
            result['status']='maintenance_notice' if notice else 'stale' if result['freshness']=='stale' else 'uncertain' if result['freshness']!='fresh' or result['visual_flags'] else 'fresh_image_review_needed'
            result['local_conditions_verified']=False
        except Exception as exc: result.update(status='unavailable',error=str(exc))
        results.append(result)
    return results


def playlist(url, depth=0):
    if depth>2: raise ValueError('Too many nested HLS playlists')
    text=get(url).text
    if not text.lstrip().startswith('#EXTM3U'): raise ValueError('Not an HLS playlist')
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    for i,line in enumerate(lines):
        if line.startswith('#EXT-X-STREAM-INF'):
            child=next((x for x in lines[i+1:] if not x.startswith('#')),None)
            if not child: raise ValueError('Missing HLS variant URL')
            return playlist(urljoin(url,child),depth+1)
    sequence=re.search(r'#EXT-X-MEDIA-SEQUENCE:(\d+)',text)
    segments=[]; duration=None; program_time=None
    for line in lines:
        if line.startswith('#EXTINF:'):
            try: duration=float(line.split(':',1)[1].split(',',1)[0])
            except ValueError: duration=None
        elif line.startswith('#EXT-X-PROGRAM-DATE-TIME:'): program_time=line.split(':',1)[1]
        elif not line.startswith('#'):
            segments.append({'url':urljoin(url,line),'duration':duration,'program_date_time':program_time})
            duration=None; program_time=None
    if not segments: raise ValueError('No HLS media segments')
    # A manifest with ENDLIST is not an ongoing live stream.
    return {'url':url,'sequence':int(sequence.group(1)) if sequence else None,
            'segments':segments,'last_segment':segments[-1]['url'],'ended':'#EXT-X-ENDLIST' in text,
            'discontinuity_present':'#EXT-X-DISCONTINUITY' in text,
            'program_date_time_present':any(s['program_date_time'] for s in segments)}


def advancing(first,second):
    a,b=first['sequence'],second['sequence']
    if first['ended'] or second['ended']: return False
    return (a is not None and b is not None and b>a) or first['last_segment']!=second['last_segment']


def decode_segment(segment, target):
    # Separate process provides a hard timeout around video decoding.
    code="import cv2,sys; c=cv2.VideoCapture(sys.argv[1]); ok,f=c.read(); c.release(); sys.exit(0 if ok and cv2.imwrite(sys.argv[2],f) else 2)"
    subprocess.run([sys.executable,'-c',code,str(segment),str(target)],timeout=20,check=True,capture_output=True)


def delray(output,previous,delay):
    result={'id':'delray','location':'Delray Beach','view':'Stream from existing plume POC',
            'page_url':DELRAY,'checked_at':utcnow().isoformat(),'freshness':'unknown',
            'capture_utc':None,'capture_time_basis':'Not verified; HLS delivery progression is not a capture timestamp'}
    try:
        first=playlist(DELRAY); time.sleep(delay); second=playlist(DELRAY)
        is_advancing=advancing(first,second)
        if not is_advancing: raise ValueError('Delray playlist did not advance during this acquisition')
        if first.get('discontinuity_present') or second.get('discontinuity_present'):
            raise ValueError('HLS discontinuity found in Delray acquisition')
        combined={item['url']:item for item in first['segments'] + second['segments']}
        ordered=list(combined.values())
        selected=[]; total=0.0
        for item in reversed(ordered):
            selected.insert(0,item); total += item.get('duration') or 0.0
            if total >= 30.0: break
        if total < 20.0: raise ValueError(f'Only {total:.1f}s of Delray footage available; need at least 20s')
        payload=b''.join(get(item['url']).content for item in selected)
        if not payload: raise ValueError('Downloaded Delray clip is empty')
        acquisition_id=hashlib.sha256(payload).hexdigest()
        segment=output/'delray_sample.ts'; temporary=output/'delray_sample.ts.tmp'
        temporary.write_bytes(payload); temporary.replace(segment)
        target=output/'delray.png'; decode_segment(segment,target)
        result.update(first_playlist=first,second_playlist=second,playlist_advancing=True,
                      acquisition_id=acquisition_id,clip_sha256=acquisition_id,
                      clip_file=segment.name,clip_duration_seconds=total,
                      segment_urls=[item['url'] for item in selected],
                      segment_count=len(selected),retrieved_at=utcnow().isoformat())
        result.update(inspect_frame(target.read_bytes(),target,previous.get('delray')))
        result['status']='stream_advancing_capture_unverified'; result['local_conditions_verified']=False
    except Exception as exc: result.update(status='unavailable',error=str(exc),acquisition_id=None)
    return [result]


def html_report(results,output,checked,max_age):
    cards=[]
    for r in results:
        image=f'<img src="{escape(r["image_file"],quote=True)}" alt="{escape(r["location"]+" "+r["view"],quote=True)}">' if r.get('image_file') else ''
        stamp=r.get('capture_utc')
        local=datetime.fromisoformat(stamp).astimezone(ZoneInfo('America/New_York')).strftime('%b %d, %Y %I:%M %p %Z') if stamp else 'Unknown'
        warnings='; '.join(r.get('visual_flags',[])) or 'No simple brightness/repeat flag; visual review still required.'
        cards.append(f'<section><h2>{escape(r["location"])}</h2><p>{escape(r["view"])}</p><h3>{escape(r["status"].replace("_"," "))}</h3>{image}<p>Capture: {local}<br>Age: {r.get("age_minutes","unknown")} minutes</p><p>{escape(warnings)}</p><p>{escape(r.get("error", ""))}</p><a href="{escape(r["page_url"],quote=True)}">Open source</a></section>')
    report=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Beach camera health</title><style>body{{font:16px system-ui;background:#06283e;color:#eef9fb;margin:auto;max-width:1200px;padding:24px}}h1,a{{color:#76ded8}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:16px}}section{{background:#123e50;padding:18px;border-radius:20px}}img{{width:100%;height:auto}}h3{{color:#ffda86}}</style><h1>PBC beach camera source check</h1><p>Checked {escape(checked)} · experimental fresh threshold {max_age:g} minutes</p><p>Each location is independent. A nearby fresh camera offers regional context, not replacement Boynton/Delray conditions. No automatic clarity, current or safety score.</p><p>Review previews for maintenance screens, night, glare and camera movement. A recent metadata timestamp does not prove a usable beach image. Stream progression does not verify capture time.</p><p>C-16 flow: unavailable · <a href="https://www.sfwmd.gov/">Open SFWMD information</a></p><div class="cards">{''.join(cards)}</div><p>Camera imagery: Palm Beach County ERM / Erdman Video Systems; Delray stream as configured in your existing POC. Source links retained.</p></html>'''
    (output/'card.html').write_text(report,encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('camera_health_output'))
    p.add_argument('--fresh-minutes',type=float,default=30)
    p.add_argument('--stream-check-seconds',type=float,default=8)
    p.add_argument('--skip-delray',action='store_true')
    args=p.parse_args()
    if args.fresh_minutes<=0 or not 1<=args.stream_check_seconds<=30: p.error('Use positive freshness and stream check of 1–30 seconds')
    args.output.mkdir(parents=True,exist_ok=True)
    state=args.output/'previous_check.json'; previous={}
    if state.exists():
        try: previous=json.loads(state.read_text(encoding='utf-8'))
        except (ValueError,OSError): pass
    results=[]
    for site in SITES: results.extend(county(site,args.output,previous,args.fresh_minutes))
    if not args.skip_delray: results.extend(delray(args.output,previous,args.stream_check_seconds))
    checked=utcnow().isoformat()
    report={'checked_at_utc':checked,'fresh_threshold_minutes':args.fresh_minutes,'cameras':results,
            'fallback_policy':'Show fresh nearby sources as separately named regional context; never substitute local current/clarity. Human visual review required.',
            'c16':{'live_flow':'unavailable','info_url':'https://www.sfwmd.gov/'}}
    (args.output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    state.write_text(json.dumps({r['id']:r for r in results},indent=2),encoding='utf-8')
    html_report(results,args.output,checked,args.fresh_minutes)
    for r in results: print(r['location'],r['view'],'=>',r['status'],r.get('age_minutes','unknown'),'minutes')
    print('Report:',(args.output/'card.html').resolve())
    return 0 if any(r.get('image_file') for r in results) else 1


if __name__=='__main__': sys.exit(main())
