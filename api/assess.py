import json,os
from urllib.request import Request,urlopen

def handler(request):
 if request.method!='POST': return {'statusCode':405,'body':'Method not allowed'}
 token=os.environ.get('DEMO_RUN_TOKEN')
 if token and request.headers.get('x-demo-token')!=token:return {'statusCode':401,'body':'Demo code required'}
 if not os.environ.get('OPENROUTER_API_KEY'):return {'statusCode':503,'body':'Jev is not configured'}
 try:
  d=request.json();kind=d['kind'];state=d['state']
  if kind not in ('supplier','retender') or len(json.dumps(state))>10000:raise ValueError('Invalid assessment')
  if kind=='supplier':question="How closely does the supplier's demonstrated prior work match the new tender's requirements?";criteria={'Strong match':'Prior work directly addresses requirements.','Possible match':'Some overlap, important details unclear.','Poor match':'Available evidence suggests materially different work.','Insufficient evidence':'Records lack enough scope detail.'}
  else:question='Does this new tender appear to procure substantially the same service or capability as the expiring contract?';criteria={'Likely related procurement':'Substantially same capability and plausible replacement.','Possibly related':'Some overlap; replacement uncertain.','Unrelated':'Different services or capabilities.','Insufficient evidence':'Descriptions do not permit a useful comparison.'}
  body=json.dumps({'model':'typesafe/jev-1.14','state':state,'questions':{'assessment':{'type':'choice','instructions':question,'criteria':criteria}}}).encode();req=Request('https://openrouter.ai/api/alpha/decisions',data=body,headers={'Authorization':'Bearer '+os.environ['OPENROUTER_API_KEY'],'Content-Type':'application/json'})
  with urlopen(req,timeout=25) as r:result=json.load(r)
  a=result['answers']['assessment']
  if a.get('type')!='choice' or a.get('choice') not in criteria:raise ValueError('Unexpected typed answer')
  return {'statusCode':200,'headers':{'Content-Type':'application/json'},'body':json.dumps({'choice':a['choice'],'probabilities':a.get('probabilities'),'model':result.get('model'),'id':result.get('id')})}
 except Exception as e:return {'statusCode':502,'headers':{'Content-Type':'application/json'},'body':json.dumps({'error':str(e)})}
