import csv,json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]; out=root/'public/data'; out.mkdir(parents=True,exist_ok=True)
files=[('openTenderNotice-ouvertAvisAppelOffres.csv','tenders.json'),('2025-2026-contractHistory-contratsOctroyes.csv','contracts-2025.json'),('2026-2027-contractHistory-contratsOctroyes.csv','contracts-2026.json')]; manifest={'files':{}}
for src,dst in files:
 p=root/'data'/src; raw=p.read_bytes()
 with p.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
 (out/dst).write_text(json.dumps(rows,ensure_ascii=False,separators=(',',':')))
 meta=json.loads(p.with_name(src+'.meta.json').read_text()); manifest['files'][dst]={'source':src,'bytes':len(raw),'rows':len(rows),'sha256':hashlib.sha256(raw).hexdigest(),'retrieved_at':meta.get('retrieved_at')}
manifest['retrieved_at']=next(iter(manifest['files'].values()))['retrieved_at'];manifest['snapshot_id']=hashlib.sha256(''.join(x['sha256'] for x in manifest['files'].values()).encode()).hexdigest();(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('prepared',sum(f['rows'] for f in manifest['files'].values()),'rows')
