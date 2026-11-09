# 🚀 Deployment Guide

## Quick Deploy Options

### Option 1: Local Development (Recommended for Demo)

```bash
# Terminal 1 - Redis + PostgreSQL, then the backend (run from the repo root)
cp .env.example .env          # then add your ANTHROPIC_API_KEY
docker compose up -d
uv sync
uv run python main.py

# Terminal 2 - Frontend
cd frontend
python -m http.server 3000

# Access: http://localhost:3000
```

### Option 2: Docker

The repo has a `Dockerfile` for the backend (runs as a non-root user, with a health check on `/health`).

```bash
docker build -t ai-sales-orchestrator .
docker run --env-file .env -p 8000:8000 ai-sales-orchestrator
```

Point `REDIS_URL` and `POSTGRES_URL` in `.env` at services the container can reach. GitHub Actions (`.github/workflows/ci.yml`) runs the tests and builds this image on every push.

### Option 3: Cloud Deployment

#### Backend: Railway / Render

1. **Create account** on Railway.app or Render.com
2. **Connect GitHub** repository
3. **Add a Redis and a PostgreSQL instance** (both platforms offer them as add-ons)
4. **Add environment variables**:
   - `ANTHROPIC_API_KEY`
   - `REDIS_URL`
   - `POSTGRES_URL`
   - `FASTAPI_PORT=8000`
   - `DEBUG_MODE=False`
5. **Deploy** - automatic!

#### Frontend: Vercel / Netlify

1. **Upload frontend folder** to Vercel/Netlify
2. **Update API_URL** in `frontend/config.js` (all pages read it from there):
   ```javascript
   const API_URL = 'https://your-backend-url.com';
   ```
3. **Deploy** - done!

## Environment-Specific Configuration

### Development
```env
DEBUG_MODE=True
ALLOWED_ORIGINS=["http://localhost:3000"]
REDIS_URL=redis://localhost:6379/0
POSTGRES_URL=postgresql://sales:sales@localhost:5432/sales
```

### Production
```env
DEBUG_MODE=False
ALLOWED_ORIGINS=["https://your-frontend-domain.com"]
ANTHROPIC_API_KEY=sk-ant-xxxxx
REDIS_URL=redis://your-redis-host:6379/0
POSTGRES_URL=postgresql://user:password@your-postgres-host:5432/sales
```

Every setting is listed in `.env.example`.

For production also set `AUTH_ENABLED=true`. Each session then gets a secret token (returned by `/api/session/create`) that every request must send in the `X-Session-Token` header; the frontend does this automatically through `frontend/config.js`.

### Secrets

Settings are read from environment variables, so any secret store works if it puts the values into the environment before the app starts (for example a systemd `EnvironmentFile=` filled from AWS SSM Parameter Store or Secrets Manager, or your host's secret settings). Do not commit `.env`.

### Monitoring endpoints

- `GET /health` returns 200 only when Redis (and Postgres, if configured) answer, otherwise 503. Use it for load balancer checks.
- `GET /metrics` exposes Prometheus metrics (request counts and times per route). Keep it off the public internet.
- Every response carries an `X-Request-ID` header, and every log line carries the same id. Set `LOG_JSON=true` for JSON logs.

## Security Checklist

- [ ] Use HTTPS in production
- [ ] Secure API keys (never commit to git)
- [ ] Set proper CORS origins
- [ ] Implement rate limiting
- [ ] Add authentication (if needed)
- [ ] Use environment variables for secrets

## Performance Optimization

### Backend
```python
# Use connection pooling for Claude API
# Cache frequent queries
# Implement request rate limiting
```

### Frontend
```javascript
// Use debouncing for user inputs
// Implement lazy loading for products
// Cache API responses
```

## Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Logs
The backend logs to the terminal it runs in (or `journalctl -u orchestrator -f` when it runs as a service, see `AWS_DEPLOYMENT.md`).

## Scaling Considerations

### For 1000+ concurrent users:
1. Use managed Redis and PostgreSQL (sessions, orders and checkpoints are already stored there)
2. Deploy multiple backend instances
3. Add load balancer
4. Use CDN for frontend
5. Implement caching strategy

## Cost Estimation

**Development (Free):**
- Claude API: Free tier (limited requests)
- Hosting: Local/GitHub Pages

**Production (Small):**
- Claude API: ~$50/month (depends on usage)
- Backend hosting: $5-10/month (Railway/Render)
- Frontend hosting: Free (Vercel/Netlify)
- **Total: ~$55-60/month**

**Production (Medium - 10k users):**
- Claude API: ~$500/month
- Backend: $50/month (scaled instances)
- Database: $25/month (PostgreSQL)
- **Total: ~$575/month**

## Support & Maintenance

### Weekly Tasks
- [ ] Check error logs
- [ ] Monitor API usage
- [ ] Review session data
- [ ] Update dependencies

### Monthly Tasks
- [ ] Security audit
- [ ] Performance review
- [ ] Cost optimization
- [ ] Feature updates

---

**For Techathon Demo:** Local deployment is perfect! ✅