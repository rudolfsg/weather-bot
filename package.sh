#!/bin/bash
rm deployment-package.zip
rm -rf venv
python3.9 -m venv venv
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt
python shrink_venv.py
pip install nbformat --force
deactivate
cd venv/lib/python3.9/site-packages
zip -r -9 ../../../../deployment-package.zip .
cd ../../../../
zip -g -9 deployment-package.zip weather.py
zip -g -9 deployment-package.zip secrets.json
aws lambda update-function-code --function-name weather-bot --zip-file fileb://deployment-package.zip