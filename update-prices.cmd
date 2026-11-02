@echo off
rem Weekly refresh of Tian's roguelike sheet + Steam prices/discounts (run by Windows Task Scheduler),
rem then posts the top-10 discounted roguelikes to Discord.
cd /d "%~dp0"
echo ==== %date% %time% ====>> update-prices.log
python -I import-roguelikes.py >> update-prices.log 2>&1
if errorlevel 1 exit /b 1
node post-to-discord.mjs >> update-prices.log 2>&1
