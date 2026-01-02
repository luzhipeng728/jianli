module.exports = {
  apps: [
    {
      name: 'jianli-final-backend',
      cwd: '/root/jianli_final/backend',
      script: '/root/jianli_final/backend/.venv/bin/uvicorn',
      args: 'app.main:app --host 0.0.0.0 --port 8002',
      interpreter: 'none',
      env: {
        PYTHONPATH: '/root/jianli_final/backend',
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
    },
    {
      name: 'jianli-final-frontend',
      cwd: '/root/jianli_final/frontend',
      script: 'npx',
      args: 'vite preview --host 0.0.0.0 --port 4173',
      watch: false,
      autorestart: true,
      max_restarts: 10,
    }
  ]
}
