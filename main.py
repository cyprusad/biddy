"""Small, auditable CanadaBuys procurement research report."""
import argparse, csv, datetime as dt, html, json, os, re, urllib.request
from urllib.parse import quote_plus
from collections import defaultdict
from pathlib import Path
from difflib import SequenceMatcher

HERE=Path(__file__).resolve().parent
DATA=HERE/'data'
MODEL='typesafe/jev-1.14'
TECH=re.compile(r'\b(software|computer|information technolog|cyber|data|cloud|network|telecom|digital|IT service|application|database|systems development|hosting|artificial intelligence|security system)\b',re.I)
STOP=set('the and for with from that this into services service supply support contract government canada department office consulting other system systems'.split())

def rows(name):
 with (DATA/name).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def get(r,*names): return next((r.get(n,'').strip() for n in names if r.get(n,'').strip()),'')
def norm(s): return re.sub(r'[^a-z0-9]+',' ',s.lower()).strip()
def tokens(s): return set(norm(s).split())-STOP
def sim(a,b):
 aa,bb=tokens(a),tokens(b)
 return len(aa&bb)/len(aa|bb) if aa|bb else 0

def tender(r):
 return {'id':get(r,'referenceNumber-numeroReference'),'solicitation':get(r,'solicitationNumber-numeroSollicitation'),'title':get(r,'title-titre-eng','title-titre-fra'),'description':get(r,'tenderDescription-descriptionAppelOffres-eng','tenderDescription-descriptionAppelOffres-fra'),'buyer':get(r,'contractingEntityName-nomEntitContractante-eng','contractingEntityName-nomEntitContractante-fra'),'published':get(r,'publicationDate-datePublication'),'closing':get(r,'tenderClosingDate-appelOffresDateCloture'),'category':get(r,'procurementCategory-categorieApprovisionnement'),'gsin':get(r,'gsin-nibs'),'unspsc':get(r,'unspsc'),'url':get(r,'noticeURL-URLavis-eng','noticeURL-URLavis-fra')}
def contract(r):
 return {'id':get(r,'referenceNumber-numeroReference','contractNumber-numeroContrat'),'contract':get(r,'contractNumber-numeroContrat'),'solicitation':get(r,'solicitationNumber-numeroSollicitation'),'title':get(r,'title-titre-eng','title-titre-fra'),'description':get(r,'tenderDescription-descriptionAppelOffres-eng','tenderDescription-descriptionAppelOffres-fra'),'buyer':get(r,'contractingEntityName-nomEntitContractante-eng','contractingEntityName-nomEntitContractante-fra'),'supplier':get(r,'supplierStandardizedName-nomNormaliseFournisseur-eng','supplierStandardizedName-nomNormaliseFournisseur-fra','supplierLegalName-nomLegalFournisseur-eng'),'end':get(r,'contractEndDate-dateFinContrat'),'award':get(r,'contractAwardDate-dateAttributionContrat'),'category':get(r,'procurementCategory-categorieApprovisionnement'),'gsin':get(r,'gsin-nibs'),'unspsc':get(r,'unspsc'),'value':get(r,'totalContractValue-valeurTotaleContrat','contractAmount-montantContrat'),'currency':get(r,'contractCurrency-contratMonnaie'),'amendment':get(r,'amendmentNumber-numeroModification'),'url':get(r,'noticeURL-URLavis-eng','noticeURL-URLavis-fra')}
def parse_date(s):
 try:return dt.date.fromisoformat(s[:10])
 except (ValueError,TypeError):return None
def category_overlap(a,b):
 return bool((a['gsin'] and a['gsin']==b['gsin']) or (a['unspsc'] and a['unspsc']==b['unspsc']) or (a['category'] and a['category'].lower()==b['category'].lower()))
def same_buyer(a,b):return norm(a['buyer'])==norm(b['buyer']) and bool(a['buyer'])
def text(a,b):return sim(a['title']+' '+a['description'],b['title']+' '+b['description'])
def source_url(o,tender=False):
 if o.get('url'): return o['url']
 term=o.get('solicitation') or o.get('id') or o.get('contract') or o.get('title','')
 tab='t' if tender else 'c'
 return 'https://canadabuys.canada.ca/en/tender-opportunities?current_tab='+tab+'&words='+quote_plus(term)

def decide(state, question, criteria):
 key=os.environ.get('OPENROUTER_API_KEY')
 if not key:return {'choice':'Not evaluated','probabilities':None,'model':None,'error':'OPENROUTER_API_KEY unavailable'}
 body=json.dumps({'model':MODEL,'state':state,'questions':{'assessment':{'type':'choice','instructions':question,'criteria':criteria}}}).encode()
 req=urllib.request.Request('https://openrouter.ai/api/alpha/decisions',data=body,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=60) as res: data=json.load(res)
  ans=data['answers']['assessment']
  if ans.get('type')!='choice':raise ValueError('Unexpected answer type')
  return {'choice':ans['choice'],'probabilities':ans.get('probabilities'),'confidence':ans.get('confidence'),'model':data.get('model',MODEL),'id':data.get('id')}
 except Exception as e:return {'choice':'Not evaluated','probabilities':None,'model':MODEL,'error':f'{type(e).__name__}: {e}'}

def esc(s):return html.escape(str(s or ''))
def link(item,label,is_tender):
 u=source_url(item,is_tender);return f'<a href="{esc(u)}">{esc(label or item["id"] or "source")}</a>'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--refresh',action='store_true');ap.add_argument('--max-tenders',type=int,default=10);ap.add_argument('--max-decisions',type=int,default=50);ap.add_argument('--evaluate',action='store_true');ap.add_argument('--reuse-decisions',action='store_true',help='reuse matching prior Jev responses without API calls');args=ap.parse_args()
 previous=[]
 if args.reuse_decisions and (HERE/'decisions.json').exists(): previous=json.loads((HERE/'decisions.json').read_text()).get('decisions',[])
 prior={(d.get('kind'),d.get('tender_id'),d.get('supplier') or d.get('contract_id')):d for d in previous}
 if args.refresh:
  import subprocess,sys
  subprocess.run([sys.executable,str(HERE/'download_data.py'),'--refresh'],check=True)
 tenders=[tender(r) for r in rows('openTenderNotice-ouvertAvisAppelOffres.csv')]
 hist=[contract(r) for fn in ('2025-2026-contractHistory-contratsOctroyes.csv','2026-2027-contractHistory-contratsOctroyes.csv') for r in rows(fn)]
 today=dt.date.today(); tenders=[t for t in tenders if parse_date(t['closing']) and parse_date(t['closing'])>=today and (TECH.search(t['title']+' '+t['description']+' '+t['category']) or TECH.search(t['gsin']))]
 # collapse amendments to the latest known row per contract/reference, with uncertain keyless records kept separate
 grouped={}
 for c in hist:
  key=c['contract'] or c['id'] or f"unkeyed:{len(grouped)}"
  old=grouped.get(key)
  if old is None or (parse_date(c['award']) or dt.date.min, int(c['amendment'] or 0) if c['amendment'].isdigit() else -1)>(parse_date(old['award']) or dt.date.min,int(old['amendment'] or 0) if old['amendment'].isdigit() else -1):grouped[key]=c
 hist=list(grouped.values())
 exp=[c for c in hist if parse_date(c['end']) and today<parse_date(c['end'])<=today+dt.timedelta(days=365)]
 tenders.sort(key=lambda x:parse_date(x['closing']) or dt.date.max); tenders=tenders[:args.max_tenders]
 supplier_pairs=[]; retender_pairs=[]; decisions=[]; count=0
 for t in tenders:
  rank=[]
  for c in hist:
   if not c['supplier']:continue
   co=category_overlap(t,c); bu=same_buyer(t,c); tx=text(t,c)
   if co or bu or tx>=.12:
    score=3*co+2*bu+tx
    rank.append((score,c,co,bu,tx))
  suppliers=defaultdict(list)
  for _,c,co,bu,tx in sorted(rank,key=lambda x:x[0],reverse=True):suppliers[c['supplier']].append((c,co,bu,tx))
  for supplier,items in sorted(suppliers.items(),key=lambda kv:max((int(x[1])+int(x[2])+x[3] for x in kv[1]),default=0),reverse=True)[:5]:
   best=items[0]; match='Not evaluated'; evidence=best[0]
   saved=prior.get(('supplier',t['id'],supplier))
   if saved:
    match=saved; decisions.append(saved); count+=1
   elif count<args.max_decisions and not (best[2] and best[3]):
    match=decide({'new_tender':{'title':t['title'],'description':t['description'],'category':t['category'] or t['gsin'] or t['unspsc']},'supplier':supplier,'prior_contracts':[{'title':x[0]['title'],'description':x[0]['description'],'reference_id':x[0]['id']} for x in items[:3]]},'How closely does the supplier\'s demonstrated prior work match the new tender\'s requirements?',{'Strong match':'Prior work directly addresses the described requirements.','Possible match':'Some meaningful overlap, but important requirements are unclear.','Poor match':'Available evidence suggests materially different work.','Insufficient evidence':'Records do not provide enough scope detail.'})
    count+=1;decisions.append({'kind':'supplier','tender_id':t['id'],'supplier':supplier,'history_ids':[x[0]['id'] for x in items[:3]],**match})
   elif best[2] and best[3]:match='Possible match (category and buyer overlap)'
   supplier_pairs.append((t,supplier,match,evidence))
 for c in exp:
  matches=[]
  for t in tenders:
   co=category_overlap(c,t);bu=same_buyer(c,t);tx=text(c,t)
   if c['solicitation'] and t['solicitation'] and norm(c['solicitation'])==norm(t['solicitation']): score=10
   else:score=3*co+2*bu+tx
   if score>=1.2:matches.append((score,t,co,bu,tx))
  if matches:
   for score,t,co,bu,tx in sorted(matches,reverse=True,key=lambda x:x[0])[:3]:
    saved=prior.get(('retender',t['id'],c['id']))
    if saved:
     rel=saved; decisions.append(saved); count+=1
    elif count<args.max_decisions and not (co and bu):
     rel=decide({'expiring_contract':{'description':c['description'],'title':c['title'],'buyer':c['buyer'],'category':c['category'] or c['gsin']},'new_tender':{'description':t['description'],'title':t['title'],'buyer':t['buyer'],'category':t['category'] or t['gsin']}},'Does this new tender appear to procure substantially the same service or capability as the expiring contract?',{'Likely related procurement':'Substantially same capability and plausible replacement.','Possibly related':'Some overlap, but replacement relationship uncertain.','Unrelated':'Different services or capabilities.','Insufficient evidence':'Descriptions do not allow a useful comparison.'})
     count+=1;decisions.append({'kind':'retender','contract_id':c['id'],'tender_id':t['id'],**rel})
     relation=rel['choice']
    else:relation='Possible retendering signal' if score>=1.2 else 'No related open tender identified'
    retender_pairs.append((c,t,relation))
  else:retender_pairs.append((c,None,'Upcoming expiry — no related open tender identified.'))
 stamp=dt.datetime.now().astimezone().isoformat(timespec='minutes')
 audit={'generated_at':stamp,'model':MODEL,'decision_limit':args.max_decisions,'decision_count':count,'candidate_pair_count':len(supplier_pairs)+sum(t is not None for _,t,_ in retender_pairs),'decisions':decisions,'inputs':{p.name:{'bytes':p.stat().st_size,'rows':sum(1 for _ in csv.DictReader(p.open(encoding='utf-8-sig',newline='')))} for p in [DATA/f for f in ('openTenderNotice-ouvertAvisAppelOffres.csv','2025-2026-contractHistory-contratsOctroyes.csv','2026-2027-contractHistory-contratsOctroyes.csv')]}}
 (HERE/'decisions.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
 def table(headers,body):return '<table><thead><tr>'+''.join(f'<th>{esc(h)}</th>' for h in headers)+'</tr></thead><tbody>'+body+'</tbody></table>'
 rows1=''.join('<tr>'+f'<td>{link(t,t["title"],True)} <small>{esc(t["id"])}</small></td><td>{esc(t["buyer"])}</td><td>{esc(t["closing"])}</td><td>{esc(s)}</td><td>{esc(m.get("choice",m) if isinstance(m,dict) else m)}</td><td>{link(c,c["title"],False)} <small>{esc(c["id"])}</small></td></tr>' for t,s,m,c in supplier_pairs)
 rows2=''.join('<tr>'+f'<td>{link(c,c["title"],False)} <small>{esc(c["id"])}</small></td><td>{esc(c["buyer"])}</td><td>{esc(c["end"])}</td><td>{link(t,t["title"],True) if t else "—"}</td><td>{esc(rel)}</td></tr>' for c,t,rel in retender_pairs)
 doc=f'''<!doctype html><html><head><meta charset="utf-8"><title>Canadian Procurement Matchmaker</title><style>body{{font:14px system-ui,sans-serif;color:#111;background:white;margin:32px}}h1{{font-size:22px}}h2{{font-size:17px;margin-top:30px}}p,small{{color:#555}}table{{border-collapse:collapse;width:100%;font-size:12px}}th,td{{text-align:left;padding:7px;border-bottom:1px solid #ccc;vertical-align:top}}th{{background:#f5f5f5}}a{{color:#111}}</style></head><body><h1>Canadian Procurement Matchmaker</h1><p>Generated {esc(stamp)} · Jev model {esc(MODEL)} · Decisions {count}/{args.max_decisions}. Historical awards indicate past work, not eligibility. Similar tenders are signals, not confirmed replacements.</p><h2>Open opportunities — potential suppliers</h2>{table(['RFP','Buyer','Closes','Potential supplier','Match','Previous contract'],rows1)}<h2>Expiring contracts — retendering signals</h2>{table(['Expiring contract','Buyer','End date','Related open RFP','Relationship'],rows2)}<p>Inputs: {audit['inputs']} · Candidate pairs: {audit['candidate_pair_count']}. Absence of a match does not establish that no replacement procurement exists.</p></body></html>'''
 (HERE/'report.html').write_text(doc)
 print(f"Wrote report.html and decisions.json; open tenders {len(tenders)}, expiring {len(exp)}, supplier pairs {len(supplier_pairs)}, retender pairs {sum(t is not None for _,t,_ in retender_pairs)}, Jev calls {count}")
if __name__=='__main__':main()
