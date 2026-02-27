@echo off
REM Quick Start Script for Multi-Tenant AI Chatbot (Windows)

echo ==========================================
echo Multi-Tenant AI Chatbot - Quick Start
echo ==========================================

REM Check if .env exists
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env
    echo.
    echo WARNING: Please edit .env and add your GEMINI_API_KEY
    echo    Get your API key from: https://makersuite.google.com/app/apikey
    echo.
    pause
)

echo.
echo Starting services with Docker Compose...
docker-compose up -d

echo.
echo Waiting for services to be healthy...
timeout /t 10 /nobreak >nul

REM Check service health
echo.
echo Checking service status...
docker-compose ps

echo.
echo Testing API health...
timeout /t 5 /nobreak >nul

curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo API is healthy!
) else (
    echo Waiting for API to start...
    timeout /t 10 /nobreak >nul
)

echo.
echo ==========================================
echo All services are running!
echo ==========================================
echo.
echo API Documentation:
echo   - Swagger UI: http://localhost:8000/docs
echo   - ReDoc:      http://localhost:8000/redoc
echo.
echo Service Ports:
echo   - API:        http://localhost:8000
echo   - PostgreSQL: localhost:5432
echo   - Redis:      localhost:6379
echo.
echo Useful Commands:
echo   - View logs:        docker-compose logs -f
echo   - Stop services:    docker-compose down
echo   - Restart services: docker-compose restart
echo   - Run tests:        python test_api.py
echo.
echo Next Steps:
echo   1. Visit http://localhost:8000/docs to explore the API
echo   2. Create a client using POST /clients
echo   3. Create a user using POST /users
echo   4. Login using POST /login to get a token
echo   5. Upload documents using POST /upload
echo   6. Start chatting using POST /chat
echo.
echo ==========================================
pause
