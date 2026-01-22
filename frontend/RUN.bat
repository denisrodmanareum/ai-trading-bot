@echo off
cd /d "%~dp0"
set NODE_OPTIONS=--openssl-legacy-provider
npm start
