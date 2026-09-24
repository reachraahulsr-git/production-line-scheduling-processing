import express from 'express';
import http from 'http';
import { spawn, ChildProcess } from 'child_process';
import path from 'path';

const app = express();
const PORT = 3000;
const PYTHON_PORT = 5000;

let pythonProcess: ChildProcess | null = null;

function startPythonApp() {
  console.log('[RUNNER] Launching Python Flask & Java Multithreaded Engine...');
  const runPy = path.join(process.cwd(), 'run.py');
  
  pythonProcess = spawn('python3', [runPy, '--port', String(PYTHON_PORT)], {
    stdio: 'inherit',
    cwd: process.cwd(),
    env: { ...process.env, PYTHONUNBUFFERED: '1' }
  });

  pythonProcess.on('error', (err) => {
    console.error('[RUNNER ERROR] Failed to start Python backend:', err);
  });

  pythonProcess.on('exit', (code, signal) => {
    console.log(`[RUNNER] Python process exited with code ${code} and signal ${signal}`);
  });
}

// Clean termination
process.on('SIGTERM', () => {
  if (pythonProcess) pythonProcess.kill('SIGTERM');
  process.exit(0);
});
process.on('SIGINT', () => {
  if (pythonProcess) pythonProcess.kill('SIGINT');
  process.exit(0);
});

startPythonApp();

// Reverse proxy all requests to Python Flask backend on port 5000
app.use((req, res) => {
  const options: http.RequestOptions = {
    hostname: '127.0.0.1',
    port: PYTHON_PORT,
    path: req.url,
    method: req.method,
    headers: {
      ...req.headers,
      host: `127.0.0.1:${PYTHON_PORT}`
    }
  };

  const proxyReq = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode || 500, proxyRes.headers);
    proxyRes.pipe(res);
  });

  proxyReq.on('error', (err) => {
    // If Python is still booting, show loading retry message
    res.status(502).send(`
      <!DOCTYPE html>
      <html>
        <head>
          <meta http-equiv="refresh" content="2">
          <title>Starting Production Engine...</title>
          <style>
            body { font-family: sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            .box { text-align: center; }
            .spinner { border: 4px solid #334155; border-top: 4px solid #0284c7; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 16px auto; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
          </style>
        </head>
        <body>
          <div class="box">
            <div class="spinner"></div>
            <h2>Starting Python & Java Production System...</h2>
            <p style="color: #94a3b8;">Initializing SQLite schema and spawning Java socket server (Port 5050)...</p>
          </div>
        </body>
      </html>
    `);
  });

  req.pipe(proxyReq);
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[GATEWAY] Gateway running on http://0.0.0.0:${PORT} (Proxying to Python Flask on port ${PYTHON_PORT})`);
});
