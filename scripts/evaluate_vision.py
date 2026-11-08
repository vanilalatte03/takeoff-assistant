"""Fixed synthetic crop evaluation; paid model calls require --live explicitly."""
from argparse import ArgumentParser
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps/api'))
from app.services import assist_vision
from app.services.provider_errors import provider_error_metadata


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


def token(kind, text, unit='unknown'):
    return {'kind': kind, 'raw_text': text, 'unit': unit, 'bbox': None}


def box_blur(pix):
    """Deterministic separable 7px box blur with clamped edge sampling."""
    width, height, channels = pix.width, pix.height, pix.n
    source = pix.samples
    horizontal = bytearray(len(source))
    blurred = bytearray(len(source))
    for y in range(height):
        for x in range(width):
            for c in range(channels):
                horizontal[(y*width+x)*channels+c] = sum(source[(y*width+min(width-1,max(0,x+d)))*channels+c] for d in range(-3,4))//7
    for y in range(height):
        for x in range(width):
            for c in range(channels):
                blurred[(y*width+x)*channels+c] = sum(horizontal[(min(height-1,max(0,y+d))*width+x)*channels+c] for d in range(-3,4))//7
    return fitz.Pixmap(fitz.csRGB, width, height, bytes(blurred), False)


def corpus():
    """Only built-in Helvetica and PyMuPDF; no user files or random generation."""
    cases = [
        ('rotated', '90-degree rotated text', [('4200 mm', (100, 210), 90)],
         [token('dimension', '4200 mm', 'mm')], 'NEEDS_REVIEW'),
        ('low_resolution', '24px raster enlarged 10x, then separable 7px box blur',
         [('2700 mm', (45, 130), 0)], [token('dimension', '2700 mm', 'mm')], 'NEEDS_REVIEW'),
        ('mixed', 'Room number, finish code and dimension share a crop',
         [('ROOM 110', (30, 65), 0), ('ACST', (30, 125), 0), ('4200 mm', (30, 185), 0)],
         [token('room_no', '110'), token('finish_code', 'ACST'), token('dimension', '4200 mm', 'mm')], 'NEEDS_REVIEW'),
        ('unitless', 'Numeric token with no printed unit; never infer mm',
         [('4200', (55, 125), 0)], [token('dimension', '4200')], 'NEEDS_REVIEW'),
        ('blank', 'White crop; explicit negative, not missing truth', [], [], 'NOT_FOUND'),
    ]
    result = []
    for name, description, texts, expected, status in cases:
        with fitz.open() as doc:
            page = doc.new_page(width=240, height=240)
            for text, point, rotate in texts:
                page.insert_text(point, text, fontsize=23, rotate=rotate, fontname='helv')
            scale = .1 if name == 'low_resolution' else 1
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            if name == 'low_resolution':
                pix = fitz.Pixmap(pix, 240, 240)
                pix = box_blur(pix)
            png = pix.tobytes('png')
        result.append(({'id': name, 'description': description, 'image_sha256': digest(png),
                        'expected': expected, 'expected_api_status': status,
                        'truth': 'explicit_synthetic', 'human_review_required': True,
                        'score_policy': 'diagnostic_only' if name == 'low_resolution' else 'exact_tokens',
                        'ambiguity': 'source token 2700 mm is not reliably legible; abstain or review, no exact accuracy score' if name == 'low_resolution' else 'none'}, png))
    return result


def score(expected, actual):
    """Exact visible-token/kind matching; whitespace normalized, numeric units kept.

    A wrong value/kind is both a missing and an unexpected token. Unit errors are
    counted only on matching kind/text pairs, avoiding invented correspondence.
    """
    def key(item):
        return item['kind'], ' '.join(item['raw_text'].split())
    truth = Counter(key(item) for item in expected)
    found = Counter(key(item) for item in actual)
    remaining = list(actual)
    units = 0
    for item in expected:
        match = next((i for i, other in enumerate(remaining) if key(other) == key(item)), None)
        if match is not None:
            units += remaining.pop(match)['unit'] != item['unit']
    return {'false_positives': sum((found-truth).values()), 'omissions': sum((truth-found).values()),
            'value_or_kind_errors': sum((found-truth).values()), 'unit_errors': units,
            'blank_false_positives': len(actual) if not expected else None}


def evaluate(*, live=False, image_dir=None):
    generated = corpus()
    truths = [case for case, _ in generated]
    config = {'endpoint': 'https://api.openai.com/v1/responses', 'max_output_tokens': 1500,
              'timeout_seconds': 30, 'store': False, 'detail': 'high', 'calls_per_case': 1,
              'model': assist_vision.settings.ai_vision_model if live else None,
              'reader_sha256': digest(Path(assist_vision.__file__).read_bytes())}
    report = {'corpus_version': 'vision-failures-v1', 'scope': 'synthetic only; not field accuracy',
              'runtime': {'pymupdf': fitz.VersionBind, 'python': sys.version.split()[0]},
              'truth_sha256': digest(json_bytes(truths)), 'configuration': config,
              'configuration_sha256': digest(json_bytes(config)),
              'mode': 'LIVE' if live else 'MANIFEST_ONLY', 'model_quality': 'NOT_RUN',
              'contract_results': 'separate pytest suites; not model quality',
              'cost': {'amount': None, 'reason': 'No verified price supplied; tokens only.'}, 'cases': []}
    if image_dir:
        image_dir.mkdir(parents=True, exist_ok=True)
    for case, png in generated:
        if image_dir:
            (image_dir / (case['id'] + '.png')).write_bytes(png)
        row = {**case, 'status': 'NOT_RUN', 'metrics': None, 'elapsed_ms': None, 'metadata': None}
        if live:
            start = perf_counter()
            try:
                output, metadata = assist_vision.read_crop(png)
                row.update(status='COMPLETED', actual=[item.model_dump() for item in output.items], metadata=metadata)
                if case['score_policy'] == 'exact_tokens':
                    row['metrics'] = score(case['expected'], row['actual'])
                else:
                    row['diagnostic'] = {'candidate_count': len(output.items), 'abstained': not output.items,
                                         'reason': 'Ambiguous raster; source truth is not legibility truth.'}
                row['api_result_equivalent'] = 'NEEDS_REVIEW' if output.items else 'NOT_FOUND'
            except Exception as exc:
                # Never serialize exception messages/provider bodies or turn failure into an empty answer.
                row.update(status='FAILED', metadata=provider_error_metadata(exc))
            row['elapsed_ms'] = round((perf_counter()-start)*1000, 3)
        report['cases'].append(row)
    if live:
        report['model_quality'] = 'EXECUTED' if all(r['status'] == 'COMPLETED' for r in report['cases']) else 'INCOMPLETE'
    return report


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--image-dir', type=Path)
    parser.add_argument('--live', action='store_true', help='Authorize five paid calls with generated synthetic PNGs only')
    parser.add_argument('--env-file', type=Path, help='Explicit caller-supplied credential file, permitted with --live only')
    parser.add_argument('--model', help='Explicit Vision model override for this live process only')
    args = parser.parse_args()
    if (args.env_file or args.model) and not args.live:
        parser.error('--env-file/--model requires --live; offline mode does not read credentials')
    if args.env_file:
        if not args.env_file.is_file():
            parser.error('explicit credential file does not exist')
        from dotenv import dotenv_values
        from pydantic import SecretStr
        credentials = dotenv_values(args.env_file, interpolate=False)
        # Read only the explicitly supplied file. No search and no model fallback.
        if credentials.get('TAKEOFF_AI_API_KEY'):
            assist_vision.settings.ai_api_key = SecretStr(credentials['TAKEOFF_AI_API_KEY'])
        if credentials.get('TAKEOFF_AI_VISION_MODEL'):
            assist_vision.settings.ai_vision_model = credentials['TAKEOFF_AI_VISION_MODEL']
        del credentials
    if args.model:
        assist_vision.settings.ai_vision_model = args.model
    report = evaluate(live=args.live, image_dir=args.image_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('model_quality='+report['model_quality'])
    return 1 if report['model_quality'] == 'INCOMPLETE' else 0


if __name__ == '__main__':
    raise SystemExit(main())
