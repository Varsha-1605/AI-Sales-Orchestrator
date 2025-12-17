# 🚀 Deployment Guide

## Quick Deploy Options

### Option 1: Local Development (Recommended for Demo)

```bash
# Terminal 1 - Backend
cd backend
python main.py

# Terminal 2 - Frontend
cd frontend
python -m http.server 3000

# Access: http://localhost:3000
```

### Option 2: Docker (Coming Soon)

```dockerfile
# Dockerfile for backend
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Option 3: Cloud Deployment

#### Backend: Railway / Render

1. **Create account** on Railway.app or Render.com
2. **Connect GitHub** repository
3. **Add environment variables**:
   - `ANTHROPIC_API_KEY`
   - `FASTAPI_PORT=8000`
   - `DEBUG_MODE=False`
4. **Deploy** - automatic!

#### Frontend: Vercel / Netlify

1. **Upload frontend folder** to Vercel/Netlify
2. **Update API_URL** in all HTML files:
   ```javascript
   const API_URL = 'https://your-backend-url.com';
   ```
3. **Deploy** - done!

## Environment-Specific Configuration

### Development
```env
DEBUG_MODE=True
ALLOWED_ORIGINS=http://localhost:3000
USE_MOCK_RESPONSES=False
```

### Production
```env
DEBUG_MODE=False
ALLOWED_ORIGINS=https://your-frontend-domain.com
USE_MOCK_RESPONSES=False
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

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
```bash
# View backend logs
tail -f backend/logs/app.log
```

## Scaling Considerations

### For 1000+ concurrent users:
1. Use Redis for session storage
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