@echo off
echo ========================================
echo Docker Build and Push Script
echo ========================================
echo.

REM Set your Docker Hub username
set DOCKER_USERNAME=your_dockerhub_username
set IMAGE_NAME=voicebot-rive
set VERSION=latest

echo Step 1: Building frontend...
cd frontend
call npm run build
if %errorlevel% neq 0 (
    echo Failed to build frontend
    pause
    exit /b 1
)

echo.
echo Step 2: Building Docker image...
cd ..\backend
docker build -t %DOCKER_USERNAME%/%IMAGE_NAME%:%VERSION% .
if %errorlevel% neq 0 (
    echo Failed to build Docker image
    pause
    exit /b 1
)

echo.
echo Step 3: Testing Docker image locally...
echo Starting container on port 8000...
docker run -d -p 8000:8000 --name voicebot-test ^
  -e DEEPGRAM_API_KEY=%DEEPGRAM_API_KEY% ^
  -e MONGODB_URL=%MONGODB_URL% ^
  -e DATABASE_NAME=bean_and_brew ^
  %DOCKER_USERNAME%/%IMAGE_NAME%:%VERSION%

if %errorlevel% neq 0 (
    echo Failed to start container
    pause
    exit /b 1
)

echo.
echo Container started! Test at http://localhost:8000
echo.
echo Press any key to stop the test container and push to Docker Hub...
pause

docker stop voicebot-test
docker rm voicebot-test

echo.
echo Step 4: Pushing to Docker Hub...
docker push %DOCKER_USERNAME%/%IMAGE_NAME%:%VERSION%

if %errorlevel% neq 0 (
    echo Failed to push to Docker Hub
    echo Make sure you're logged in: docker login
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS!
echo ========================================
echo Image: %DOCKER_USERNAME%/%IMAGE_NAME%:%VERSION%
echo.
echo To deploy on Cloud Run:
echo gcloud run deploy voicebot --image %DOCKER_USERNAME%/%IMAGE_NAME%:%VERSION% --platform managed --region us-central1 --allow-unauthenticated --port 8000
echo.
pause
