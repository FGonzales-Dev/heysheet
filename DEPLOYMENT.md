# HeySheet Deployment Guide

## Why Separate Apps?

The previous monolithic deployment was causing 404 errors due to:
- Port conflicts between frontend (3000) and backend (8080) 
- Routing conflicts (both trying to handle root path)
- Complex build dependencies
- CORS issues with hard-coded URLs

## Deployment Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Frontend App  │    │   Backend App   │
│  (Static Site)  │───▶│  (Web Service)  │
│                 │    │                 │
│ React + Vite    │    │ Django + PostgreSQL │
└─────────────────┘    └─────────────────┘
```

## Deployment Checklist

### Backend Deployment
- [ ] Deploy using `.do/backend-app.yaml`
- [ ] Verify database connection
- [ ] Test `/api/health/` endpoint
- [ ] Note backend URL for frontend config

### Frontend Deployment  
- [ ] Update `.do/frontend-app.yaml` with backend URL
- [ ] Deploy as static site
- [ ] Verify React app loads
- [ ] Test API calls to backend

### Post-Deployment
- [ ] Update backend CORS settings with frontend URL
- [ ] Test end-to-end functionality
- [ ] Monitor logs for any errors

## Configuration Files

- `.do/backend-app.yaml` - Backend service configuration
- `.do/frontend-app.yaml` - Frontend static site configuration
- `Dockerfile.backend` - Improved backend container

## Environment Variables

### Backend Required
- `DJANGO_SECRET_KEY` - Django secret key
- `GROQ_API_KEY` - Groq API key for AI features
- `GOOGLE_SHEETS_CREDENTIALS` - Service account JSON
- `SPREADSHEET_ID` - Google Sheets ID
- Database variables (auto-injected by DigitalOcean)

### Frontend Required
- `VITE_API_URL` - Backend API URL

## Troubleshooting

### 404 Errors
- Check routing configuration in app specs
- Verify both apps are deployed successfully
- Check CORS settings match exact URLs

### CORS Errors
- Ensure frontend URL is in backend's `CORS_ALLOWED_ORIGINS`
- Verify `CSRF_TRUSTED_ORIGINS` includes frontend URL
- Check environment variables are properly set

### Build Failures
- Check build logs in DigitalOcean console
- Verify all dependencies are in requirements.txt/package.json
- Ensure source directories are correct in app specs
