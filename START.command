#!/bin/bash
# Double-click this file to launch the Financial Dashboard Generator.
cd "$(dirname "$0")"

# Install / update dependencies if needed
venv/bin/pip install -q -r requirements.txt

# Open the browser tab automatically, then start Streamlit
open http://localhost:8501
venv/bin/python3 -m streamlit run web_app.py --server.headless true
