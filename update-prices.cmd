@echo off
rem Weekly refresh of Tian's roguelike sheet + Steam prices/discounts (run by Windows Task Scheduler).
cd /d "%~dp0"
echo ==== %date% %time% ====>> update-prices.log
python -I import-roguelikes.py >> update-prices.log 2>&1
