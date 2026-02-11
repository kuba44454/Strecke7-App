@echo off
cd /d "%~dp0"
echo Uruchamianie Treningu Strecke 7...
echo Nie zamykaj tego okna, dopoki uzywasz aplikacji.
python -m streamlit run app.py --server.address=127.0.0.1
pause