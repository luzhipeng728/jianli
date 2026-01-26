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
        ES_HOST: 'localhost',
        ES_PORT: '9200',
        REDIS_HOST: 'localhost',
        REDIS_PORT: '6379',
        REDIS_URL: 'redis://localhost:6379/0',
        DASHSCOPE_API_KEY: process.env.DASHSCOPE_API_KEY || '',
        JWT_SECRET: 'your_jwt_secret_key_here_please_change_in_production',
        DEBUG: 'True',
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
    },
    {
      name: 'interview-frontend',
      cwd: '/root/jianli_final/interview-frontend',
      script: 'npx',
      args: 'vite preview --host 0.0.0.0 --port 5174',
      watch: false,
      autorestart: true,
      max_restarts: 10,
    }
  ]
}
