# CryptoMarket Railway Deployment Configuration

## Deployment Steps

### 1. Create a Railway Account
- Visit https://railway.app  
- Click "Login" → choose "Continue with GitHub"  
- Complete authorization  

### 2. Create a New Project
- Click "New Project"  
- Select "Deploy from GitHub repo"  
- Choose your CryptoMarket repository (must be pushed to GitHub first)  

### 3. Configure Environment Variables
In Project Settings → Variables, add:

```
PORT=8000
```

### 4. Deployment
Railway will automatically detect the Python project and deploy it  

### 5. Get Your Domain
- After deployment, go to Project → Settings → Domains  
- A domain like `xxx.up.railway.app` will be generated automatically  
- Or bind a custom domain  

## Notes

1. **Free Tier**: $5/month or 500 hours of runtime  
2. **Sleep Mechanism**: Service sleeps after 15 minutes of inactivity; next request takes ~10–30 seconds to wake  
3. **Data Persistence**: Data may be lost after restart on the free tier. Recommended:
   - Use Railway Volumes (paid)  
   - Or manually update data files regularly  

## Local Development

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Access http://localhost:8000

