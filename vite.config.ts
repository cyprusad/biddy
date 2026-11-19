import { defineConfig, loadEnv } from 'vite';
import { assess } from './api/assess.js';
export default defineConfig(({ mode }) => {
  const env = { ...process.env, ...loadEnv(mode, process.cwd(), '') };
  return { esbuild: { jsx: 'automatic' }, plugins: [{
    name: 'local-jev-api', configureServer(server) {
      server.middlewares.use('/api/assess', async (req, res) => {
        res.setHeader('Cache-Control', 'no-store');
        if(req.method==='GET'){res.setHeader('Content-Type','application/json');res.end(JSON.stringify({requiresDemoCode:Boolean(env.DEMO_RUN_TOKEN),enabled:Boolean(env.DEMO_RUN_TOKEN&&env.OPENROUTER_API_KEY)}));return;}
        if (req.method !== 'POST') { res.statusCode=405;res.end(JSON.stringify({error:'POST required.'}));return; }
        let raw=''; for await (const chunk of req) { raw += chunk; if(raw.length>700000){res.statusCode=413;res.end(JSON.stringify({error:'Request too large.'}));return;} }
        try { const result=await assess(JSON.parse(raw),env,req.headers);res.statusCode=result.status;res.setHeader('X-Assessment-Trace',result.body.traceId);res.setHeader('Content-Type','application/json');res.end(JSON.stringify(result.body)); }
        catch { res.statusCode=400;res.setHeader('Content-Type','application/json');res.end(JSON.stringify({error:'Invalid JSON request.'})); }
      });
    }
  }] };
});
