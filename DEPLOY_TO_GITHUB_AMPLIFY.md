# 🚀 Deploy Frontend to GitHub and AWS Amplify

## Step 1: Create GitHub Repository

### Option A: Using GitHub CLI (Recommended)

```bash
# Install GitHub CLI if not installed
# Ubuntu/Debian:
sudo apt install gh

# Login to GitHub
gh auth login

# Create repository and push
cd "/media/vijay/6FFF-F894/Serverless Geospatial Analysis Framework"
gh repo create sgaf-geospatial --public --source=. --remote=origin --push
```

### Option B: Using GitHub Web Interface

1. Go to https://github.com/new
2. Repository name: `sgaf-geospatial`
3. Description: "Serverless Geospatial Analysis Framework - 14+ AWS Services"
4. Choose **Public**
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

Then run:
```bash
cd "/media/vijay/6FFF-F894/Serverless Geospatial Analysis Framework"
git remote add origin https://github.com/YOUR_USERNAME/sgaf-geospatial.git
git branch -M main
git push -u origin main
```

## Step 2: Connect to AWS Amplify

### Method 1: Using AWS Amplify Console (Easiest)

1. **Go to AWS Amplify Console:**
   - Open: https://console.aws.amazon.com/amplify/
   - Click "New app" → "Host web app"

2. **Connect Repository:**
   - Select "GitHub"
   - Authorize AWS Amplify to access your GitHub account
   - Select repository: `sgaf-geospatial`
   - Select branch: `main`
   - Click "Next"

3. **Configure Build Settings:**
   - App name: `sgaf-frontend`
   - Environment: `production`
   - Build settings: The `amplify.yml` file will be automatically detected
   - Review the build settings (should show):
     ```yaml
     version: 1
     frontend:
       phases:
         preBuild:
           commands:
             - echo "No build commands needed for static site"
         build:
           commands:
             - echo "Building frontend..."
       artifacts:
         baseDirectory: frontend
         files:
           - '**/*'
     ```

4. **Configure Environment Variables (Optional):**
   - Click "Advanced settings"
   - Add environment variables if needed:
     - `API_URL` = `https://pkj2v7ecf3.execute-api.us-east-1.amazonaws.com/prod/`
     - (Note: API URL is already hardcoded in app.js)

5. **Review and Deploy:**
   - Click "Save and deploy"
   - Wait for deployment (5-10 minutes)
   - Your app will be live at: `https://main.xxxxx.amplifyapp.com`

### Method 2: Using Amplify CLI

```bash
# Install Amplify CLI
npm install -g @aws-amplify/cli

# Configure Amplify
amplify configure

# Initialize Amplify in project
cd "/media/vijay/6FFF-F894/Serverless Geospatial Analysis Framework"
amplify init

# Add hosting
amplify add hosting

# Publish
amplify publish
```

## Step 3: Verify Deployment

1. **Check Amplify Console:**
   - Go to AWS Amplify Console
   - Click on your app
   - View deployment status
   - Click on the app URL to open it

2. **Test the Frontend:**
   - Open the Amplify URL
   - Upload a test file
   - Verify real-time status updates
   - Check results display

## Step 4: Custom Domain (Optional)

1. In Amplify Console, go to "Domain management"
2. Click "Add domain"
3. Enter your domain name
4. Follow the DNS configuration instructions

## Troubleshooting

### Build Fails
- Check build logs in Amplify Console
- Verify `amplify.yml` is correct
- Ensure `frontend/` directory exists

### API Not Working
- Verify API Gateway URL in `frontend/app.js`
- Check CORS settings in API Gateway
- Verify API Gateway is deployed

### Frontend Not Loading
- Check browser console for errors
- Verify all files are in `frontend/` directory
- Check Amplify build logs

## Quick Commands

```bash
# Push updates to GitHub
git add .
git commit -m "Update frontend"
git push origin main
# Amplify will automatically redeploy!

# Check deployment status
aws amplify list-apps
aws amplify list-branches --app-id YOUR_APP_ID
```

## Success!

Your amazing frontend is now:
- ✅ Deployed to GitHub
- ✅ Connected to AWS Amplify
- ✅ Automatically deploying on every push
- ✅ Live and accessible worldwide!

🎉 **Congratulations! Your SGAF frontend is now live!**

