"""Download/cache official inputs. Standard library only; no model calls."""
import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

BASE = 'https://canadabuys.canada.ca/opendata/pub/'
FILES = [
    'openTenderNotice-ouvertAvisAppelOffres.csv',
    '2025-2026-contractHistory-contratsOctroyes.csv',
    '2026-2027-contractHistory-contratsOctroyes.csv',
]
DICTIONARY = 'https://donnees-data.tpsgc-pwgsc.gc.ca/ba2/ac-cb/achatscanada-canadabuys-dd.xml'


def inspect_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        if not fields or len(fields) < 2 or any('<html' in f.lower() for f in fields):
            raise ValueError('Response is not a recognizable CSV table')
        count = 0
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f'CSV column count mismatch at record {count + 1}')
            count += 1
        return fields, count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent / 'data')
    args = parser.parse_args()
    args.data_dir.mkdir(parents=True, exist_ok=True)
    failed = False
    for name in FILES + ['canadabuys-data-dictionary.xml']:
        path = args.data_dir / name
        url = BASE + name if name in FILES else DICTIONARY
        meta_path = path.with_name(name + '.meta.json')
        temporary = path.with_name(name + '.part')
        try:
            if args.refresh or not path.exists():
                with urlopen(url, timeout=90) as response:
                    with temporary.open('wb') as out:
                        while chunk := response.read(1024 * 1024):
                            out.write(chunk)
                if name in FILES:
                    inspect_csv(temporary)
                else:
                    import xml.etree.ElementTree as ET
                    ET.parse(temporary)
                temporary.replace(path)
                meta_path.write_text(json.dumps({
                    'source_url': url,
                    'retrieved_at': datetime.now(timezone.utc).isoformat(),
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                }, indent=2) + '\n')
            metadata = json.loads(meta_path.read_text()) if meta_path.exists() else {}
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            retrieved = metadata.get('retrieved_at') if metadata.get('sha256') == digest else None
            print(f'{name}: {path.stat().st_size:,} bytes; retrieved: {retrieved or "unknown (manual/untracked file)"}')
            if name in FILES:
                fields, count = inspect_csv(path)
                print(f'  Rows: {count:,}\n  Columns: {json.dumps(fields, ensure_ascii=False)}')
        except (URLError, OSError, ValueError, csv.Error) as exc:
            failed = True
            print(f'{name}: {type(exc).__name__}: {exc}')
            print(f'  Download manually from {url}\n  Save as {path}')
            if path.exists():
                print('  Existing cached file preserved; rerun without --refresh to reuse it.')
        finally:
            temporary.unlink(missing_ok=True)
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
