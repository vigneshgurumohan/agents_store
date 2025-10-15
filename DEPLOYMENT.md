# 🚀 Deployment Guide

This guide will help you deploy the Agents Marketplace to Render.

## 📋 Prerequisites

1. **GitHub Account** - Your code should be in a GitHub repository
2. **Render Account** - Sign up at [render.com](https://render.com)
3. **Repository Access** - Make sure your repository is public or you have Render connected to your GitHub

## 🎯 Render Deployment Steps

### Step 1: Prepare Your Repository

1. **Commit all changes**
   ```bash
   git add .
   git commit -m "Initial commit: Agents Marketplace"
   git push origin main
   ```

2. **Verify files are present**
   - ✅ `render.yaml` (deployment configuration)
   - ✅ `backend/requirements.txt` (Python dependencies)
   - ✅ `backend/main.py` (FastAPI application)
   - ✅ `backend/data/` (CSV data files)
   - ✅ `frontend/` (HTML files)

### Step 2: Create Render Web Service

1. **Go to Render Dashboard**
   - Visit [render.com](https://render.com)
   - Sign in to your account

2. **Create New Web Service**
   - Click "New +"
   - Select "Web Service"
   - Connect your GitHub repository

3. **Configure the Service**
   - **Name**: `agents-marketplace` (or your preferred name)
   - **Environment**: `Python 3`
   - **Branch**: `main`
   - **Build Command**: `cd backend && pip install -r requirements.txt`
   - **Start Command**: `cd backend && python start_production.py`

### Step 3: Environment Variables (Optional)

If you need custom configuration:

- **DATA_SOURCE**: `csv` (default)
- **API_HOST**: `0.0.0.0` (default)
- **API_PORT**: `8000` (default)

### Step 4: Deploy

1. **Click "Create Web Service"**
2. **Wait for deployment** (usually 2-5 minutes)
3. **Check logs** for any errors

### Step 5: Verify Deployment

Once deployed, test these URLs:

- **Health Check**: `https://your-app.onrender.com/api/health`
- **Agents Listing**: `https://your-app.onrender.com/agents`
- **API Documentation**: `https://your-app.onrender.com/docs`
- **Individual Agent**: `https://your-app.onrender.com/agent/earnings-analyst`

## 🔧 Troubleshooting

### Common Issues

1. **Build Fails**
   - Check `requirements.txt` for correct dependencies
   - Ensure all files are committed to Git

2. **Server Won't Start**
   - Check `start_production.py` exists
   - Verify Python version compatibility

3. **Data Not Loading**
   - Ensure `backend/data/` folder is included
   - Check CSV file encoding

4. **Frontend Not Loading**
   - Verify `frontend/` folder is present
   - Check static file serving in `main.py`

### Debug Commands

```bash
# Check if server starts locally
cd backend
python start_production.py

# Test API endpoints
curl http://localhost:8000/api/health

# Check data loading
python test_api.py
```

## 📊 Monitoring

### Render Dashboard

- **Logs**: View real-time logs in Render dashboard
- **Metrics**: Monitor CPU, memory usage
- **Health**: Check service health status

### Health Endpoint

The application provides a health endpoint:
```
GET /api/health
```

Response:
```json
{
  "status": "healthy",
  "data_source": "csv"
}
```

## 🔄 Updates and Maintenance

### Deploying Updates

1. **Make changes** to your code
2. **Commit and push** to GitHub
3. **Render auto-deploys** from main branch

### Database Migration (Future)

If you switch to PostgreSQL:

1. **Create PostgreSQL service** in Render
2. **Update environment variables**
3. **Set DATA_SOURCE=postgres**
4. **Add database credentials**

## 💰 Cost Considerations

### Free Tier Limits

- **750 hours/month** of runtime
- **0.5 GB RAM**
- **Service sleeps** after 15 minutes of inactivity
- **Cold start** takes ~30 seconds

### Upgrade Options

- **Starter Plan**: $7/month for always-on service
- **Standard Plan**: $25/month for better performance

## 🎉 Success!

Once deployed, your Agents Marketplace will be live at:
`https://your-app-name.onrender.com`

Share the link with your team and users!

---

**Need Help?**
- Check Render documentation: [render.com/docs](https://render.com/docs)
- Review application logs in Render dashboard
- Test locally first with `python start_production.py`
