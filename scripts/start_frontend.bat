@echo off
cd /d "%~dp0\..\frontend"
if not exist "node_modules" (
    echo Installing frontend dependencies...
    npm install
)
echo.
echo Starting frontend on http://localhost:5173
npm run dev
