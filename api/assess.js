import { randomUUID } from 'node:crypto';

const MODEL = 'typesafe/jev-1.14';
// Log responses only: never request headers, credentials, or evidence bodies.
const log = (level, event, fields) => console[level]('[jev-assess]', JSON.stringify({ event, ...fields }));
const criteria = {
  supplier: {
    question: (id) => `For candidate ${id}, how closely does this supplier's demonstrated prior work match the new tender's requirements? Use only the candidate's records in state.`,
    options: { 'Strong match': 'Prior work directly addresses the described requirements.', 'Possible match': 'Some meaningful overlap, but important requirements are unclear.', 'Poor match': 'Available evidence suggests materially different work.', 'Insufficient evidence': 'The records do not provide enough scope detail.' }
  },
  retender: {
    question: (id) => `For candidate ${id}, does the new tender appear to procure substantially the same service or capability as the expiring contract? Use only its records in state.`,
    options: { 'Likely related procurement': 'Substantially the same capability and plausible replacement.', 'Possibly related': 'Some overlap, but a replacement relationship is uncertain.', 'Unrelated': 'Different services or capabilities.', 'Insufficient evidence': 'The descriptions do not permit a useful comparison.' }
  }
};
export async function assess(payload, env = process.env, headers = {}) {
  const traceId = randomUUID();
  const started = Date.now();
  const pairs = payload?.pairs;
  const finish = (status, body, reason) => {
    if (typeof body.error === 'string') {
      for (const secret of [env.OPENROUTER_API_KEY, env.DEMO_RUN_TOKEN]) {
        if (secret) body.error = body.error.split(secret).join('[redacted]');
      }
    }
    log(status >= 500 ? 'error' : status >= 400 ? 'warn' : 'info', 'request_finished', {
      traceId, status, reason, durationMs: Date.now() - started, response: body
    });
    return { status, body: { ...body, traceId } };
  };
  const code = env.DEMO_RUN_TOKEN;
  if (!code) return finish(503, { error: 'Jev is disabled until DEMO_RUN_TOKEN is configured.' }, 'demo_code_not_configured');
  if (headers['x-demo-token'] !== code) return finish(401, { error: 'Demo code required.' }, 'demo_code_rejected');
  const key = env.OPENROUTER_API_KEY;
  if (!key) return finish(503, { error: 'Jev is not configured on this server.' }, 'key_not_configured');
  if (!Array.isArray(pairs) || pairs.length < 1 || pairs.length > 50) return finish(400, { error: 'Send between 1 and 50 candidate pairs.' }, 'invalid_pair_count');
  if (pairs.some(p => !p || typeof p.id !== 'string' || !p.id)) return finish(400, { error: 'Each candidate needs an ID.' }, 'invalid_pair_id');
  if (new Set(pairs.map(p => p.id)).size !== pairs.length) return finish(400, { error: 'Candidate IDs must be unique.' }, 'duplicate_pair_ids');
  const questions = {};
  const statePairs = [];
  for (let i = 0; i < pairs.length; i++) {
    const pair = pairs[i], spec = Object.hasOwn(criteria, pair.kind) ? criteria[pair.kind] : null;
    const stateCharacters = pair.state ? JSON.stringify(pair.state).length : 0;
    if (!spec || !stateCharacters || stateCharacters > 12000) {
      return finish(400, { error: 'Invalid candidate pair.' }, 'invalid_pair');
    }
    const qid = `pair_${i}`;
    statePairs.push({ id: qid, evidence: pair.state });
    questions[qid] = { type: 'choice', instructions: spec.question(qid), criteria: spec.options };
  }
  try {
    const response = await fetch('https://openrouter.ai/api/alpha/decisions', {
      method: 'POST', headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: MODEL, state: { candidates: statePairs }, questions }), signal: AbortSignal.timeout(55000)
    });
    const data = await response.json();
    if (!response.ok) return finish(response.status, { error: data?.error?.message || 'OpenRouter rejected the request.' }, 'openrouter_rejected');
    const answers = pairs.map((pair, i) => {
      const answer = data.answers?.[`pair_${i}`], spec = criteria[pair.kind];
      if (!answer || answer.type !== 'choice' || !Object.hasOwn(spec.options, answer.choice)) {
        throw new Error(`Invalid response for candidate ${pair.id}`);
      }
      return { id: pair.id, choice: answer.choice, probabilities: answer.probabilities || null, confidence: answer.confidence ?? null };
    });
    return finish(200, { model: data.model || MODEL, requestId: data.id || null, usage: data.usage || null, answers }, 'success');
  } catch (error) {
    return finish(502, { error: error.message || 'Jev request failed.' }, 'upstream_failure');
  }
}
export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method === 'GET') {
    const health = { requiresDemoCode: Boolean(process.env.DEMO_RUN_TOKEN), enabled: Boolean(process.env.DEMO_RUN_TOKEN && process.env.OPENROUTER_API_KEY) };
    log('info', 'availability_checked', health);
    return res.status(200).json(health);
  }
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST required.' });
  const result = await assess(req.body, process.env, req.headers);
  res.setHeader('X-Assessment-Trace', result.body.traceId);
  return res.status(result.status).json(result.body);
}
