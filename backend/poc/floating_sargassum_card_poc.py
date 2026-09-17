"""USF offshore sargassum source POC. Not a beaching forecast.

Dependencies: requests numpy Pillow. Run --help for live and offline examples.
No credentials, camera, current or wind integration required.
"""
import argparse
import base64
from datetime import date, datetime, timedelta, timezone
from html import escape, unescape
from io import BytesIO
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image
import requests

HOST = 'https://optics.marine.usf.edu'
PATTERN = re.compile(r'^[cC](\d{4})(\d{3})(\d{4})(\d{3})\.1KM\.GCOOS\.(1DAY|7DAY)\.L3D\.(FAD|FA_DENSITY)\.png$')
REGIONS = {'boynton_delray': (-80.15, 26.3, -79.85, 26.7),
           'palm_beach_to_miami': (-80.4, 25.5, -79.7, 27.0)}
BASE_COLORS = {'background': (0, 0, 102), 'land': (101, 67, 33),
               'missing': (0, 0, 0), 'coastline': (255, 255, 255)}


def fetch(url):
    if urlparse(url).hostname != 'optics.marine.usf.edu':
        raise ValueError('Only USF source URLs are supported.')
    r = requests.get(url, timeout=(10, 45))
    r.raise_for_status()
    if len(r.content) > 25_000_000:
        raise ValueError('Unexpectedly large response.')
    return r.content


def metadata(filename):
    m = PATTERN.fullmatch(filename)
    if not m:
        raise ValueError('Require original full-size GCOOS FA_DENSITY or FAD filename; SST, renamed files and thumbnails are rejected.')
    y1, d1, y2, d2, period, product = m.groups()
    start = date(int(y1), 1, 1) + timedelta(days=int(d1)-1)
    end = date(int(y2), 1, 1) + timedelta(days=int(d2)-1)
    if start.year != int(y1) or end.year != int(y2) or (end-start).days != (6 if period == '7DAY' else 0):
        raise ValueError('Invalid image date interval.')
    return {'filename': filename, 'period_start': str(start), 'period_end': str(end),
            'product': product, 'composite': period, 'nominal_resolution_m': 1000}


def discover(day, period):
    page_url = f'{HOST}/cgi-bin/optics_data?roi=GCOOS&Date={day.month}/{day.day}/{day.year}'
    page = fetch(page_url).decode('utf-8', errors='replace')
    candidates = []
    for tag in re.findall(r'<a\b[^>]*>', page, re.S):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', tag))
        path = unescape(attrs.get('data-url', ''))
        name = path.rsplit('/', 1)[-1]
        try:
            meta = metadata(name)
        except ValueError:
            continue
        if meta['composite'] != period or meta['period_end'] != str(day):
            continue
        rel = unescape(attrs.get('rel', '')).split(';')
        if len(rel) < 2 or 'colorbar_fa_density' not in rel[1]:
            continue
        candidates.append((urljoin(HOST, path), urljoin(HOST, rel[1]), meta))
    if not candidates:
        raise ValueError(f'No full-size {period} FA product with linked legend found for {day}. Try an explicit earlier date; no silent substitution.')
    candidates.sort(key=lambda c: c[2]['product'] != 'FAD')
    return (*candidates[0], page_url)


def get_bounds(filename):
    url = f'{HOST}/cgi-bin/ge?file={filename}'
    root = ET.fromstring(fetch(url))
    # Select the overlay for THIS image, not the legend or current vectors.
    for overlay in root.findall('.//{*}GroundOverlay'):
        href = overlay.findtext('.//{*}Icon/{*}href', '')
        if filename not in href:
            continue
        box = overlay.find('.//{*}LatLonBox')
        if box is None or float(box.findtext('{*}rotation', '0')) != 0:
            raise ValueError('Unsupported rotated/missing georeferencing.')
        return tuple(float(box.findtext('{*}'+key)) for key in ('west','south','east','north'))
    raise ValueError('Image georeferencing not found.')


def crop_box(region, bounds, size):
    w, s, e, n = bounds
    rw, rs, re_, rn = region
    width, height = size
    if not (w <= rw < re_ <= e and s <= rs < rn <= n):
        raise ValueError('Requested region lies outside source bounds.')
    # Small epsilon avoids a spurious extra pixel from floating point error.
    return (math.floor((rw-w)/(e-w)*width+1e-8), math.floor((n-rn)/(n-s)*height+1e-8),
            math.ceil((re_-w)/(e-w)*width-1e-8), math.ceil((n-rs)/(n-s)*height-1e-8))


def legend_palette(image):
    a = np.asarray(image.convert('RGB'))
    # A vertical or horizontal colorbar: use the line with most distinct colors.
    lines = [a[y, :, :] for y in range(a.shape[0])] + [a[:, x, :] for x in range(a.shape[1])]
    line = max(lines, key=lambda x: len(np.unique(x, axis=0)))
    palette = np.unique(line, axis=0)
    # Exclude text, background and known map-mask colors from detection candidates.
    keep = np.ones(len(palette), dtype=bool)
    for color in BASE_COLORS.values():
        keep &= np.max(np.abs(palette.astype(int)-color), axis=1) > 2
    keep &= np.ptp(palette.astype(int), axis=1) > 12
    palette = palette[keep]
    if len(palette) < 32:
        raise ValueError('Could not extract a usable legend ramp; refusing arbitrary color classes.')
    return palette.astype(np.int16)


def analyze(image, palette):
    a = np.asarray(image.convert('RGB')).reshape(-1, 3).astype(np.int16)
    masks = {name: np.all(a == color, axis=1) for name, color in BASE_COLORS.items()}
    excluded = np.logical_or.reduce(list(masks.values()))
    # Only match source legend colors. Do not call all bright/colorful pixels algae.
    matches = np.zeros(len(a), dtype=bool)
    for start in range(0, len(a), 512):
        chunk = a[start:start+512]
        distance = np.max(np.abs(chunk[:, None, :]-palette[None, :, :]), axis=2)
        matches[start:start+len(chunk)] = np.min(distance, axis=1) <= 2
    matches &= ~excluded
    unknown = ~(excluded | matches)
    counts = {name: int(mask.sum()) for name, mask in masks.items()}
    counts.update(legend_matched=int(matches.sum()), unrecognized=int(unknown.sum()), total=len(a))
    possible_water = len(a)-counts['land']-counts['coastline']
    recognized = counts['background']+counts['legend_matched']
    quality = 'limited' if not possible_water or recognized/possible_water < .7 else 'usable for exploratory image reading'
    status = ('Image colors consistent with sargassum' if counts['legend_matched'] else
              'No sargassum image colors identified' if recognized else 'Insufficient image data')
    return {'status': status, 'image_readability': quality, 'pixel_counts': counts,
            'recognized_water_pixels_pct': round(100*recognized/possible_water, 2) if possible_water else None,
            'colored_pixels_pct_of_recognized_water': round(100*counts['legend_matched']/recognized, 2) if recognized else None,
            'beach_seaweed_level': 'unknown', 'beaching_prediction': 'not provided',
            'interpretation': 'Color matches are an exploratory rendered-image proxy, not measured algae coverage percent, biomass or beach severity. Blue background is not proof of algae-free water. Black and unmatched pixels remain unknown.'}


def png_data(image):
    buf = BytesIO()
    image.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


def write_report(out, report, crops, legend):
    out.mkdir(parents=True, exist_ok=True)
    (out/'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    cards = []
    for name, result in report['regions'].items():
        crops[name].save(out/f'{name}.png')
        c = result['pixel_counts']
        cards.append(f'''<section><h2>{escape(name.replace('_',' ').title())}</h2>
<h3>{escape(result['status'])}</h3><p>{escape(result['image_readability'])}</p>
<img class="crop" src="data:image/png;base64,{png_data(crops[name])}" alt="Original crop enlarged without smoothing">
<p>{c['legend_matched']} legend-matched pixels · {c['background']} background pixels<br>
{c['missing']} missing · {c['unrecognized']} unrecognized</p>
<p><b>Beach conditions: unknown</b><br>No arrival forecast or snorkeling score.</p></section>''')
    source = report['source']
    html = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Offshore sargassum source POC</title><style>body{{font:16px system-ui;background:#06283e;color:#edf9fa;margin:0;padding:24px;max-width:1000px;margin:auto}}h1{{color:#76ded8}}.grid{{display:flex;flex-wrap:wrap;gap:20px}}section{{background:#123e50;padding:20px;border-radius:20px;flex:1;min-width:260px}}h3{{color:#ffda86}}.crop{{height:330px;max-width:100%;object-fit:contain;image-rendering:pixelated}}a{{color:#76ded8}}small{{color:#c3d7df}}</style>
<h1>Offshore sargassum observations</h1><p>EXPERIMENTAL SOURCE POC · NOT A BEACH FORECAST</p>
<p>{escape(source['period_start'])} through {escape(source['period_end'])} · {escape(source['product'])} · {escape(source['composite'])} · nominal 1 km</p>
<p>{escape(report['freshness'])}</p><div class="grid">{''.join(cards)}</div>
<h2>Source legend</h2><img src="data:image/png;base64,{png_data(legend)}" alt="USF sargassum surface coverage legend">
<p>The legend measures sargassum surface-area coverage. The pixel counts above measure colored image cells, not that coverage value. Low-end colors may be below useful detection precision.</p>
<p>Currents and wind: not integrated. Beach camera: compare observations manually for this date. Retain mismatches as evidence, not as reasons to tune this card until it says High.</p>
<p>Source: USF Optical Oceanography Laboratory. <a href="{escape(source.get('page_url') or HOST, quote=True)}">Source page</a></p>
<small>Rectangular coastal windows include offshore context; they are not a fixed-distance strip from the beach. Mask semantics and palette matching require validation before production use.</small></html>'''
    (out/'card.html').write_text(html, encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--date', default=str(date.today()), help='USF end date YYYY-MM-DD (default today, no fallback)')
    p.add_argument('--period', choices=['1DAY','7DAY'], default='7DAY')
    p.add_argument('--image', type=Path, help='Offline original full-size USF PNG')
    p.add_argument('--legend', type=Path, help='Required with --image: matching source legend PNG')
    p.add_argument('--bounds', nargs=4, type=float, metavar=('WEST','SOUTH','EAST','NORTH'), help='Required offline: verified full image outer-edge bounds')
    p.add_argument('--output', type=Path, default=Path('sargassum_card_output'))
    args = p.parse_args()
    try:
        if args.image:
            if not args.legend or not args.bounds:
                raise ValueError('Offline mode requires --legend and verified --bounds WEST SOUTH EAST NORTH.')
            meta = metadata(args.image.name)
            image = Image.open(args.image).convert('RGB')
            legend = Image.open(args.legend).convert('RGB')
            bounds = tuple(args.bounds)
            meta.update(mode='offline', page_url=None, bounds_provenance='operator supplied; not checked online')
        else:
            day = date.fromisoformat(args.date)
            image_url, legend_url, meta, page_url = discover(day, args.period)
            image = Image.open(BytesIO(fetch(image_url))).convert('RGB')
            legend = Image.open(BytesIO(fetch(legend_url))).convert('RGB')
            bounds = get_bounds(meta['filename'])
            meta.update(mode='online', image_url=image_url, legend_url=legend_url, page_url=page_url, bounds_provenance='USF KML outer-edge bounds')
        if image.size != (2090, 1430) or not np.allclose(bounds, (-98,18,-79,31), atol=.001):
            raise ValueError('Unexpected GCOOS dimensions/extent; review georeferencing before analysis.')
        palette = legend_palette(legend)
        age = (date.today()-date.fromisoformat(meta['period_end'])).days
        freshness = f'Historical image: composite ended {age} days ago.' if age > 2 else f'Composite ended {age} days ago; not a live observation.'
        report = {'source':meta, 'source_bounds_wsen':bounds, 'checked_at_utc':datetime.now(timezone.utc).isoformat(),
                  'freshness':freshness, 'legend_palette_colors':len(palette), 'regions':{}}
        crops = {}
        for name, region in REGIONS.items():
            box = crop_box(region, bounds, image.size)
            crops[name] = image.crop(box)
            report['regions'][name] = dict(analyze(crops[name], palette), requested_bounds_wsen=region, crop_ltrb_exclusive=box)
        write_report(args.output, report, crops, legend)
        print('\n=== FLOATING SARGASSUM CARD POC ===')
        print(meta['filename'], '\n'+freshness)
        for name, result in report['regions'].items():
            print(f"{name}: {result['status']} | {result['image_readability']}")
            print('  Pixels:', result['pixel_counts'])
        print('Beach impact: UNKNOWN. Wind/current forecast: NOT PROVIDED.')
        print('Card:', (args.output/'card.html').resolve())
        print('JSON:', (args.output/'result.json').resolve())
        return 0
    except (ValueError, OSError, requests.RequestException, ET.ParseError) as exc:
        print(f'SOURCE POC FAILED: {exc}', file=sys.stderr)
        print('No seaweed conclusion generated. Check date/product/connectivity.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
