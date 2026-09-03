@echo off
echo =========================================================
echo Pushing NotebookLM Automation System to GitHub Repository
echo Repo: https://github.com/Somnathmodak25/Notebooklm_auto.git
echo =========================================================

REM 1. Set or update remote
git remote remove my_origin 2>nul
git remote add my_origin https://github.com/Somnathmodak25/Notebooklm_auto.git
echo Added remote 'my_origin' -> https://github.com/Somnathmodak25/Notebooklm_auto.git

REM 2. Stage files (ignoring private tokens and credentials)
git add .gitignore .env.example DEPLOYMENT.md gateway hermes scripts storage/tokens/.gitkeep storage/db/.gitkeep

REM 3. Commit
git commit -m "feat: complete notebooklm automation system, hermes skill, and fastapi gateway"

REM 4. Push to main branch
echo Pushing to GitHub...
git push -u my_origin main

echo =========================================================
echo Done! Pushed to https://github.com/Somnathmodak25/Notebooklm_auto.git
echo =========================================================
pause
