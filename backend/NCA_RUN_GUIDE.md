# How to Run NCA Toolkit API

This guide shows you how to run the NCA Toolkit API locally or in production.

## 🚀 Quick Start - Run Locally with Docker (Easiest)

### Prerequisites

- Docker installed on your system
  - **macOS**: Download from https://www.docker.com/products/docker-desktop
  - **Linux**: `sudo apt-get install docker.io`
  - **Windows**: Download Docker Desktop

### Step 1: Clone the Repository

```bash
# Navigate to a directory where you want to clone it
cd ~/Projects  # or any directory you prefer

# Clone the repository
git clone https://github.com/stephengpope/no-code-architects-toolkit.git
cd no-code-architects-toolkit
```

### Step 2: Build the Docker Image

```bash
docker build -t no-code-architects-toolkit .
```

**Note**: This may take 5-10 minutes the first time as it downloads all dependencies.

### Step 3: Run the Container

```bash
# Run with a simple API key
docker run -d -p 8080:8080 \
  --name nca-toolkit \
  -e API_KEY=your_api_key_here \
  no-code-architects-toolkit
```

**That's it!** The API is now running at `http://localhost:8080`

### Step 4: Verify It's Running

```bash
# Check health endpoint
curl http://localhost:8080/v1/toolkit/health
```

You should see a JSON response indicating the API is healthy.

### Step 5: Configure Your Django Project

Now configure your RedNote Django project to use it:

**Option A: Environment Variables**
```bash
export NCA_API_URL="http://localhost:8080"
export NCA_API_KEY="your_api_key_here"
export NCA_API_ENABLED="true"
```

**Option B: Edit settings.py**
```python
# rednote_project/settings.py
NCA_API_URL = 'http://localhost:8080'
NCA_API_KEY = 'your_api_key_here'
NCA_API_ENABLED = True
NCA_API_TIMEOUT = 600
```

### Step 6: Test It

Restart your Django server and try transcribing a video. It should be much faster now!

## 📦 Docker Commands Reference

### Start the Container
```bash
docker start nca-toolkit
```

### Stop the Container
```bash
docker stop nca-toolkit
```

### View Logs
```bash
docker logs nca-toolkit
```

### View Real-time Logs
```bash
docker logs -f nca-toolkit
```

### Remove the Container
```bash
docker stop nca-toolkit
docker rm nca-toolkit
```

### Restart the Container
```bash
docker restart nca-toolkit
```

## 🔧 Advanced Configuration

### Run with Custom Storage (Optional)

If you want to use cloud storage for processed files:

**For S3-compatible storage:**
```bash
docker run -d -p 8080:8080 \
  --name nca-toolkit \
  -e API_KEY=your_api_key_here \
  -e S3_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com \
  -e S3_ACCESS_KEY=your_access_key \
  -e S3_SECRET_KEY=your_secret_key \
  -e S3_BUCKET_NAME=your_bucket_name \
  -e S3_REGION=nyc3 \
  no-code-architects-toolkit
```

**For Google Cloud Storage:**
```bash
docker run -d -p 8080:8080 \
  --name nca-toolkit \
  -e API_KEY=your_api_key_here \
  -e GCP_SA_CREDENTIALS='{"your":"service_account_json"}' \
  -e GCP_BUCKET_NAME=your_gcs_bucket_name \
  no-code-architects-toolkit
```

### Performance Tuning

For better performance with large files:

```bash
docker run -d -p 8080:8080 \
  --name nca-toolkit \
  -e API_KEY=your_api_key_here \
  -e MAX_QUEUE_LENGTH=10 \
  -e GUNICORN_WORKERS=4 \
  -e GUNICORN_TIMEOUT=300 \
  -e LOCAL_STORAGE_PATH=/tmp \
  no-code-architects-toolkit
```

## 🌐 Run in Production

### Option 1: Google Cloud Run (Cheapest)

**Best for**: Pay only when processing

1. **Prerequisites**:
   - Google Cloud account
   - gcloud CLI installed

2. **Deploy**:
```bash
# Authenticate
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Build and push to Container Registry
docker build -t gcr.io/YOUR_PROJECT_ID/nca-toolkit .
docker push gcr.io/YOUR_PROJECT_ID/nca-toolkit

# Deploy to Cloud Run
gcloud run deploy nca-toolkit \
  --image gcr.io/YOUR_PROJECT_ID/nca-toolkit \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars API_KEY=your_api_key_here \
  --memory 16Gi \
  --cpu 4 \
  --timeout 300
```

3. **Get the URL**:
```bash
gcloud run services describe nca-toolkit --region us-central1
```

4. **Configure Django**:
```python
NCA_API_URL = 'https://your-service-url.run.app'
NCA_API_KEY = 'your_api_key_here'
NCA_API_ENABLED = True
```

### Option 2: Digital Ocean App Platform

**Best for**: Simple deployment

1. Create a new app on Digital Ocean
2. Connect your GitHub repository
3. Set environment variables:
   - `API_KEY`
   - Storage credentials (if needed)
4. Deploy

### Option 3: Your Own Server

**Best for**: Full control

```bash
# On your server (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install docker.io

# Clone and run
git clone https://github.com/stephengpope/no-code-architects-toolkit.git
cd no-code-architects-toolkit
docker build -t no-code-architects-toolkit .
docker run -d -p 8080:8080 \
  --restart always \
  -e API_KEY=your_api_key_here \
  no-code-architects-toolkit
```

## ✅ Verification

### Test Health Endpoint

```bash
curl http://localhost:8080/v1/toolkit/health
```

Expected response:
```json
{"status": "healthy", "version": "..."}
```

### Test Transcription (Example)

```bash
curl -X POST http://localhost:8080/v1/video/transcribe \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://example.com/video.mp4"}'
```

### Check in Django

1. Start your Django server
2. Go to admin panel
3. Try transcribing a video
4. Should be **10-100x faster** with API!

## 🐛 Troubleshooting

### API Not Starting

**Check Docker logs:**
```bash
docker logs nca-toolkit
```

**Check if port is available:**
```bash
lsof -ti:8080
# If something is using it, kill it or use a different port
```

**Use different port:**
```bash
docker run -d -p 8081:8080 \
  -e API_KEY=your_api_key_here \
  no-code-architects-toolkit
```

Then update Django settings:
```python
NCA_API_URL = 'http://localhost:8081'
```

### Connection Errors

**Check if API is running:**
```bash
curl http://localhost:8080/v1/toolkit/health
```

**Check API key:**
- Make sure API key matches in both Docker and Django settings

**Check network:**
- If running Docker in a VM, use the VM's IP address
- For remote servers, use the server's IP or domain

### Performance Issues

**Increase resources:**
```bash
docker run -d -p 8080:8080 \
  --name nca-toolkit \
  -e API_KEY=your_api_key_here \
  -e GUNICORN_WORKERS=8 \
  -e GUNICORN_TIMEOUT=600 \
  --memory="8g" \
  --cpus="4" \
  no-code-architects-toolkit
```

## 📋 Quick Reference

### Minimum Setup (Local)
```bash
# 1. Clone
git clone https://github.com/stephengpope/no-code-architects-toolkit.git
cd no-code-architects-toolkit

# 2. Build
docker build -t no-code-architects-toolkit .

# 3. Run
docker run -d -p 8080:8080 \
  --name nca-toolkit \
  -e API_KEY=your_api_key_here \
  no-code-architects-toolkit

# 4. Verify
curl http://localhost:8080/v1/toolkit/health

# 5. Configure Django
export NCA_API_URL="http://localhost:8080"
export NCA_API_KEY="your_api_key_here"
export NCA_API_ENABLED="true"
```

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_KEY` | ✅ Yes | - | API key for authentication |
| `S3_ENDPOINT_URL` | ❌ No | - | S3-compatible storage endpoint |
| `S3_ACCESS_KEY` | ❌ No | - | S3 access key |
| `S3_SECRET_KEY` | ❌ No | - | S3 secret key |
| `S3_BUCKET_NAME` | ❌ No | - | S3 bucket name |
| `GCP_SA_CREDENTIALS` | ❌ No | - | GCP service account JSON |
| `GCP_BUCKET_NAME` | ❌ No | - | GCP bucket name |
| `MAX_QUEUE_LENGTH` | ❌ No | 0 | Max concurrent tasks |
| `GUNICORN_WORKERS` | ❌ No | CPU+1 | Number of workers |
| `GUNICORN_TIMEOUT` | ❌ No | 30 | Request timeout |
| `LOCAL_STORAGE_PATH` | ❌ No | /tmp | Temp storage path |

## 🎯 Next Steps

1. ✅ Run NCA Toolkit API (follow steps above)
2. ✅ Configure Django settings
3. ✅ Test transcription - should be much faster!
4. ✅ Enjoy 10-100x faster processing!

## 📚 Additional Resources

- **GitHub Repository**: https://github.com/stephengpope/no-code-architects-toolkit
- **Postman Template**: Available in the GitHub repo
- **Community**: https://skool.com/no-code-architects

---

**Need Help?** Check the troubleshooting section or the main NCA Toolkit repository for support.

