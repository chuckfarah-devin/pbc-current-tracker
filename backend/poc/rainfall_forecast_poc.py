"""Rainfall source POC: completed 24-hour estimate, forward 24 hours, local daily outlook.
Requires requests and tzdata (on Windows). No rain-gauge or runoff measurement implied.
"""
import argparse
from datetime import datetime, timedelta, timezone
from html import escape
import json
import math
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
import requests

API = 'https://api.open-meteo.com/v1/forecast'
LOCAL = 'America/New_York'


def valid(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v >= 0


def category(mm):
    inches = mm/25.4
    return ('LITTLE OR NO RAIN' if inches < .1 else 'LIGHT RAIN' if inches < .5
            else 'MODERATE RAIN' if inches < 1 else 'HEAVY RAIN')


def wind_reading(data, instant):
    hours = data.get('hourly', {})
    units = data.get('hourly_units', {})
    times = hours.get('time', [])
    epoch = int(instant.timestamp())
    index = times.index(epoch) if epoch in times else None
    def value(key, unit):
        values = hours.get(key, [])
        if index is None or len(values) != len(times) or units.get(key) != unit:
            return None
        v = values[index]
        return v if valid(v) else None
    speed = value('wind_speed_10m', 'kn')
    gust = value('wind_gusts_10m', 'kn')
    direction = value('wind_direction_10m', '°')
    if direction is not None and direction > 360: direction = None
    if direction is not None: direction %= 360
    # At exact zero speed, a direction arrow has no useful meaning.
    toward = (direction+180)%360 if direction is not None and speed is not None and speed > 0 else None
    compass = lambda d: ['N','NE','E','SE','S','SW','W','NW'][int((d+22.5)//45)%8]
    return {'time_utc':instant.isoformat(), 'speed_kn':speed,
            'speed_mph':round(speed*1.150779,2) if speed is not None else None,
            'gust_kn':gust, 'gust_period':'preceding hour maximum',
            'from_degrees':direction, 'from_compass':compass(direction) if direction is not None else None,
            'toward_degrees':toward, 'toward_compass':compass(toward) if toward is not None else None,
            'status':'unavailable' if speed is None else 'calm' if speed == 0 else 'partial' if direction is None else 'available'}


def window(hourly, start, end):
    """Precipitation timestamp denotes the END of the preceding hourly accumulation."""
    if hourly.get('hourly_units', {}).get('precipitation') != 'mm':
        raise ValueError('Expected precipitation in mm.')
    times = hourly.get('hourly', {}).get('time', [])
    values = hourly.get('hourly', {}).get('precipitation', [])
    if len(times) != len(values) or len(set(times)) != len(times):
        raise ValueError('Hourly arrays differ in length or contain duplicate timestamps.')
    lookup = dict(zip(times, values))
    expected = list(range(int(start.timestamp())+3600, int(end.timestamp())+1, 3600))
    available = [lookup[t] for t in expected if t in lookup and valid(lookup[t])]
    complete = len(available) == len(expected)
    total = sum(available) if complete else None
    return {'start_utc':start.isoformat(), 'end_utc':end.isoformat(),
            'expected_hours':len(expected), 'available_hours':len(available),
            'status':'complete' if complete else 'incomplete',
            'mm':round(total,3) if total is not None else None,
            'inches':round(total/25.4,3) if total is not None else None,
            'category':category(total) if complete else 'INSUFFICIENT DATA'}


def summarize(hourly, daily, now):
    if now.tzinfo is None:
        raise ValueError('Reference time must include a timezone.')
    now = now.astimezone(timezone.utc)
    anchor = now.replace(minute=0, second=0, microsecond=0)
    local_date = now.astimezone(ZoneInfo(LOCAL)).date()
    if daily.get('daily_units', {}).get('precipitation_sum') != 'mm':
        raise ValueError('Expected daily precipitation in mm.')
    dates = daily.get('daily', {}).get('time', [])
    vals = daily.get('daily', {}).get('precipitation_sum', [])
    if len(dates) != len(vals) or len(set(dates)) != len(dates):
        raise ValueError('Invalid daily arrays.')
    lookup = dict(zip(dates, vals))
    outlook = []
    for i in range(7):
        day = str(local_date+timedelta(days=i))
        mm = lookup.get(day)
        outlook.append({'date':day, 'label':'Today (whole day)' if i==0 else day,
                        'mm':mm if valid(mm) else None,
                        'inches':round(mm/25.4,3) if valid(mm) else None,
                        'category':category(mm) if valid(mm) else 'UNAVAILABLE'})
    return {'reference_time_utc':now.isoformat(), 'display_timezone':LOCAL,
            'source':'Open-Meteo weather model estimates and forecasts; not a rain gauge',
            'recent_24h':window(hourly, anchor-timedelta(hours=24), anchor),
            'forward_24h':window(hourly, anchor, anchor+timedelta(hours=24)),
            'daily_outlook':outlook,
            'wind_now':wind_reading(hourly,anchor),
            'wind_next_12h':[wind_reading(hourly,anchor+timedelta(hours=i)) for i in range(1,13)],
            'runoff_impact':'Not measured. Rainfall alone does not establish runoff, water clarity or swimming safety.',
            'category_note':'Experimental amount bands retained from the original POC; not validated runoff thresholds.'}


def get(params):
    r = requests.get(API, params=params, timeout=(10,30))
    r.raise_for_status()
    data = r.json()
    if data.get('error'): raise ValueError(data.get('reason', 'API error'))
    return data


def render(report, output):
    def amount(item):
        return 'Unavailable' if item['mm'] is None else f"{item['inches']:.2f} in / {item['mm']:.1f} mm"
    def local(iso):
        return datetime.fromisoformat(iso).astimezone(ZoneInfo(LOCAL)).strftime('%b %d, %I:%M %p %Z')
    cards = ''
    for key, title in [('recent_24h','Previous 24 completed hours'), ('forward_24h','Forward 24-hour forecast')]:
        item = report[key]
        cards += f"<section><h2>{title}</h2><strong>{amount(item)}</strong><h3>{item['category']}</h3><p>{local(item['start_utc'])}<br>through {local(item['end_utc'])}</p><small>{item['available_hours']}/{item['expected_hours']} hourly values available</small></section>"
    rows = ''.join(f"<tr><td>{d['label']}</td><td>{amount(d)}</td><td>{d['category']}</td></tr>" for d in report['daily_outlook'])
    wind = report['wind_now']
    def speed_text(v): return 'Unavailable' if v is None else f'{v:.1f} kn'
    bearing = wind['toward_degrees']
    arrow = '' if bearing is None else f'<g transform="rotate({bearing} 100 100)"><path d="M100 48 L83 79 L94 79 L94 146 L106 146 L106 79 L117 79 Z" fill="#76ded8"/></g>'
    compass = f'<svg viewBox="0 0 200 200" width="200" role="img" aria-label="Wind blowing toward {wind["toward_compass"] or "unknown"}"><circle cx="100" cy="100" r="76" fill="#06283e" stroke="#678a9a"/><g fill="#eef9fb" text-anchor="middle" font-size="14"><text x="100" y="17">N</text><text x="190" y="105">E</text><text x="100" y="196">S</text><text x="10" y="105">W</text></g>{arrow}</svg>'
    direction_text = 'Calm; direction omitted' if wind['status']=='calm' else 'Direction unavailable' if bearing is None else f'From {wind["from_compass"]} ({wind["from_degrees"]:.0f}°) · blowing toward {wind["toward_compass"]}'
    wind_rows = ''.join(f'<tr><td>{local(w["time_utc"])}</td><td>{speed_text(w["speed_kn"])}</td><td>{"Calm" if w["status"]=="calm" else "From "+(w["from_compass"] or "unknown")}</td><td>{speed_text(w["gust_kn"])}</td></tr>' for w in report['wind_next_12h'])
    wind_html = f'<section><h2>Wind · 10 m model estimate</h2><strong>{speed_text(wind["speed_kn"])}</strong><p>{direction_text}</p>{compass}<p>Gusts: {speed_text(wind["gust_kn"])} (preceding hour max)</p><p>Valid: {local(wind["time_utc"])}</p><p>Arrow shows where air is moving. This is wind, not water current.</p></section><details><summary>Next 12 hours of wind</summary><div class="table"><table><tr><th>Valid time</th><th>Speed</th><th>Direction</th><th>Gusts</th></tr>{wind_rows}</table></div></details>'
    html = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Rainfall POC</title>
<style>body{{font:16px system-ui;background:#06283e;color:#eef9fb;max-width:980px;margin:auto;padding:24px}}h1,strong{{color:#76ded8}}strong{{font-size:28px}}.cards{{display:flex;gap:16px;flex-wrap:wrap}}section{{flex:1;min-width:240px;background:#123e50;padding:20px;border-radius:20px}}td{{padding:12px;border-bottom:1px solid #486574}}.table{{overflow:auto}}a{{color:#76ded8}}</style>
<h1>Rain & wind around Ocean Ridge</h1><p>SOURCE POC · MODEL ESTIMATES, NOT STATION OBSERVATIONS</p><p>{escape(report['mode'])} · Reference: {local(report['reference_time_utc'])}</p>{wind_html}<div class="cards">{cards}</div>
<p>The recent window ends at the latest completed hour. The forward window starts there and may include the elapsed portion of the current hour.</p>
<h2>Seven-day local outlook</h2><p>Today includes the whole calendar day, not just remaining rainfall. Daily totals overlap the windows above; do not add them together.</p><div class="table"><table>{rows}</table></div>
<p>{escape(report['runoff_impact'])}</p><p>{escape(report['category_note'])}</p><p><a href="https://open-meteo.com/">Weather data by Open-Meteo</a></p></html>'''
    output.mkdir(parents=True, exist_ok=True)
    (output/'card.html').write_text(html,encoding='utf-8')
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--latitude',type=float,default=26.53)
    p.add_argument('--longitude',type=float,default=-80.05)
    p.add_argument('--output',type=Path,default=Path('rainfall_card_output'))
    p.add_argument('--input',type=Path,help='Replay a previously saved raw_response.json without network')
    args=p.parse_args()
    try:
        if args.input:
            raw=json.loads(args.input.read_text(encoding='utf-8'))
            now=datetime.fromisoformat(raw['reference_time_utc'])
        else:
            if not (-90<=args.latitude<=90 and -180<=args.longitude<=180): raise ValueError('Invalid coordinates.')
            now=datetime.now(timezone.utc)
            common={'latitude':args.latitude,'longitude':args.longitude,'precipitation_unit':'mm','forecast_days':7}
            # UTC Unix hourly timestamps avoid DST ambiguity. Daily dates are separately local.
            raw={'reference_time_utc':now.isoformat(), 'requested_location':{'latitude':args.latitude,'longitude':args.longitude},
                 'hourly_response':get(dict(common,hourly='precipitation,wind_speed_10m,wind_direction_10m,wind_gusts_10m',wind_speed_unit='kn',past_days=2,timezone='UTC',timeformat='unixtime')),
                 'daily_response':get(dict(common,daily='precipitation_sum',timezone=LOCAL))}
        report=summarize(raw['hourly_response'],raw['daily_response'],now)
        report['mode']='Offline replay (historical snapshot)' if args.input else 'Live API fetch'
        report['requested_location']=raw.get('requested_location')
        report['api_grid_location']={key:raw['hourly_response'].get(key) for key in ('latitude','longitude','elevation')}
        render(report,args.output)
        (args.output/'raw_response.json').write_text(json.dumps(raw,indent=2),encoding='utf-8')
        print('\n=== RAINFALL SOURCE POC ===')
        for key in ('recent_24h','forward_24h'):
            item=report[key]
            print(f"{key}: {item['mm']} mm | {item['category']} | {item['available_hours']}/24 hours")
            print(item['start_utc'],'through',item['end_utc'])
        print(report['source']); print(report['runoff_impact'])
        print('Wind:', report['wind_now'])
        print('Card:',(args.output/'card.html').resolve())
        return 0
    except (ValueError,OSError,KeyError,TypeError,requests.RequestException) as exc:
        print(f'Rainfall POC failed: {exc}. No new conclusion generated; older output files may remain.',file=sys.stderr)
        return 1

if __name__=='__main__': sys.exit(main())
