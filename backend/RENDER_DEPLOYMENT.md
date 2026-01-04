# Render Deployment Guide

## Prerequisites

- Render account (https://render.com)
- GitHub repository with your code
- MongoDB Atlas database
- Deepgram API key

## Deployment Steps

### Option 1: Using render.yaml (Recommended)

1. **Push your code to GitHub**
   ```bash
   git add .
   git commit -m "Add Render deployment config"
   git push
   ```

2. **Connect to Render**
   - Go to https://dashboard.render.com
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Select the repository
   - Render will detect `render.yaml` automatically

3. **Configure Environment Variables**
   
   In Render dashboard, set these secret environment variables:
   
   - `DEEPGRAM_API_KEY` - Your Deepgram API key
   - `MONGODB_URL` - Your MongoDB Atlas connection string
   - `GOOGLE_CREDENTIALS_JSON` - (Optional) Google API credentials
   - `GOOGLE_TOKEN_GMAIL_JSON` - (Optional) Gmail token
   - `GOOGLE_TOKEN_CALENDAR_JSON` - (Optional) Calendar token

4. **Deploy**
   - Click "Apply" to create the service
   - Render will build and deploy automatically

### Option 2: Manual Setup

1. **Create New Web Service**
   - Go to Render Dashboard
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Configure Service**
   - **Name**: voiceagent-backend
   - **Region**: Oregon (or closest to you)
   - **Branch**: main
   - **Root Directory**: backend
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

3. **Add Environment Variables** (same as above)

4. **Deploy**

## Post-Deployment

### Get Your Service URL
After deployment, Render provides a URL like:
```
https://voiceagent-backend.onrender.com
```

### Test the Service
```bash
# Health check
curl https://your-service.onrender.com/health

# WebSocket endpoint
wss://your-service.onrender.com/ws
```

### Update Frontend
Update your frontend's `.env.local` with the backend URL:
```
VITE_BACKEND_URL=https://your-service.onrender.com
```

## Important Notes

### Free Tier Limitations
- Service spins down after 15 minutes of inactivity
- First request after spin-down takes ~30 seconds
- 750 hours/month free

### Upgrade to Paid Plan
For production use, consider upgrading to:
- **Starter Plan** ($7/month) - Always on, no spin-down
- **Standard Plan** ($25/month) - More resources

### Logs and Monitoring
- View logs in Render Dashboard → Your Service → Logs
- Health checks run automatically at `/health`

### Automatic Deploys
- Render auto-deploys on git push to main branch
- Disable in Settings if you want manual deploys

## Troubleshooting

### Build Fails
- Check Python version (should be 3.11)
- Verify all dependencies in requirements.txt
- Check build logs in Render dashboard

### Service Won't Start
- Verify environment variables are set
- Check MongoDB connection string
- Review startup logs

### WebSocket Connection Issues
- Ensure frontend uses `wss://` (not `ws://`)
- Check CORS settings if needed
- Verify WebSocket endpoint: `/ws`

### Slow First Response
- This is normal on free tier (cold start)
- Upgrade to paid plan for always-on service
- Model preloading happens at startup

## Monitoring

### Health Check
Render automatically monitors `/health` endpoint

### Custom Monitoring
Add monitoring services:
- Sentry for error tracking
- LogDNA/Datadog for logs
- UptimeRobot for uptime monitoring

## Scaling

### Horizontal Scaling
- Upgrade plan for multiple instances
- Configure in Service Settings → Scaling

### Resource Limits
- Free: 512 MB RAM
- Starter: 512 MB RAM
- Standard: 2 GB RAM

## Support

- Render Docs: https://render.com/docs
- Community: https://community.render.com
