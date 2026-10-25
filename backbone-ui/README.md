# CS 2200 AI TA — Backbone

## Setup

### 1. Create Virtual Environment
```bash
python3 -m venv backbone-ui
source backbone-ui/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r streamlit-rag-app/requirements.txt
```

### 3. Environment Variables
Make sure your Ollama server is running and the following env vars are set:
```bash
export LOCAL_OLLAMA_SERVER="http://localhost:11434"
export OLLAMA_PUBLIC_KEY=""
```

## Running the App

### Start Ollama Server
```bash
ollama serve
```

### Option A: New Frontend (recommended)
```bash
cd streamlit-rag-app/src
uvicorn api:app --reload --port 8000
```
Then open **http://localhost:8000** in your browser.

### Option B: Legacy Streamlit App
```bash
cd streamlit-rag-app/src
streamlit run app.py
```
