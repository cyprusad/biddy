const MODEL = 'typesafe/jev-1.14';
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
  const code = env.DEMO_RUN_TOKEN;
  if (code && headers['x-demo-token'] !== code) return { status: 401, body: { error: 'Demo code required.' } };
  const key = env.OPENROUTER_API_KEY;
  if (!key) return { status: 503, body: { error: 'Jev is not configured on this server.' } };
  const pairs = payload?.pairs;
  if (!Array.isArray(pairs) || pairs.length < 1 || pairs.length > 50) return { status: 400, body: { error: 'Send between 1 and 50 candidate pairs.' } };
  if (new Set(pairs.map(p => p.id)).size !== pairs.length) return { status: 400, body: { error: 'Candidate IDs must be unique.' } };
  const questions = {};
  const statePairs = [];
  for (let i = 0; i < pairs.length; i++) {
    const pair = pairs[i], spec = criteria[pair.kind];
    if (!spec || !pair.state || JSON.stringify(pair.state).length > 12000) return { status: 400, body: { error: 'Invalid candidate pair.' } };
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
    if (!response.ok) return { status: response.status, body: { error: data?.error?.message || 'OpenRouter rejected the request.' } };
    const answers = pairs.map((pair, i) => {
      const answer = data.answers?.[`pair_${i}`], spec = criteria[pair.kind];
      if (!answer || answer.type !== 'choice' || !Object.hasOwn(spec.options, answer.choice)) throw new Error(`Invalid response for candidate ${pair.id}`);
      return { id: pair.id, choice: answer.choice, probabilities: answer.probabilities || null, confidence: answer.confidence ?? null };
    });
    return { status: 200, body: { model: data.model || MODEL, requestId: data.id || null, answers } };
  } catch (error) { return { status: 502, body: { error: error.message || 'Jev request failed.' } }; }
}
export default async function handler(req, res) {
  if (req.method === 'GET') return res.status(200).json({ requiresDemoCode: Boolean(process.env.DEMO_RUN_TOKEN) });
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST required.' });
  const result = await assess(req.body, process.env, req.headers);
  return res.status(result.status).json(result.body);
}
