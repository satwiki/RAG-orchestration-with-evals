---
title: RAG with Evaluations Samples
description: Sample RAG applications and evaluation workflows across multiple agent frameworks
---

Sample retrieval-augmented generation (RAG) applications with reusable prompts,
local data sources, and evaluation workflows for LangGraph and Microsoft Agent
Framework.

## Setup

Python 3.11 or later is required. From the repository root, create a virtual
environment and install the dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create a `.env` file in the repository root (from `.env.example`) with your Microsoft Foundry or
Azure OpenAI or OpenAI model settings. Do not commit this file.

```dotenv
AZURE_AI_FOUNDRY_ENDPOINT=https://<resource>.openai.azure.com
AZURE_AI_FOUNDRY_API_KEY=<api-key>
AZURE_AI_FOUNDRY_DEPLOYMENT=<deployment-name>
```

Create the local sample database:

```powershell
python src/local_db/ecommerce/populate_db.py --overwrite
```

Start the Streamlit application:

```powershell
streamlit run src/main.py
```

Run DeepEval against the ecommerce sales analytics goldens:

```powershell
python src/evals/run_deepeval.py
```

Execution accuracy only, without an LLM judge:

```powershell
python src/evals/run_deepeval.py --skip-llm
```