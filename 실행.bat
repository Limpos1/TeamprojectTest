@echo off
start "Planit Backend" cmd /k "cd /d %~dp0 && python -m uvicorn server:app --reload"
start "Planit Checklist" cmd /k "cd /d %~dp0\Planit-Web-Checklist-main && gradlew bootRun"
start "Planit Auth" cmd /k "cd /d %~dp0\Planit-Web-Auth-Plan-Quiz-master\Planit-Web-Auth-Plan-Quiz-master\backend && gradlew bootRun"
start "Planit Frontend" cmd /k "cd /d %~dp0\frontend && npm run dev"