# RAG-with-evals

This is a repo to contain code for various RAG use cases, with a focus on evaluation of the output.

## Folder Structure
### Key Directories
- `src/`: Contains the main source code for the RAG samples.
  - `notebooks/`: Jupyter notebooks where I experiment. Do not refer to these unless explicitely sent as part of a request.
  - `local_db/`: Contains schema and seeding for local SQLite databases as source of truth and the db.
  - `agentic-langgraph/`: Contains code written on the LangChain and LangGraph ecosystem.
  - `agentic-maf/`: Contains code written on the Microsoft Agent Framework ecosystem.
  - `evals/`: Contains code for evaluation of RAG outputs, including metrics and evaluation scripts.
    - `ground_truth/`: Contains ground truth data generator and seeding for evaluation.
  - `skills/`: Contains reusable skills that can be used across different frameworks code.
  - `prompts/`: Contains prompts for LLMs in .txt format. The idea is to re-use the same prompt in different frameworks. The prompt should be framework-agnostic and should not contain any framework-specific syntax. Preferably in `.md` format.
    - `<framework>/utils/`: Contains utility functions and shared methods.
- `tests/`: Comprehensive test suite. Separate the tests for each framework under `tests/langgraph` and `tests/maf`.

### Technology Stack
Use the following technologies in this repo. If you need to add another tech, ask first.
- **Language**: Python 3.11+
- **Framework**: Langchain, LangGraph, Microsoft Agent Framework, FastAPI
- **AI**: Azure Foundry and Azure OpenAI, HuggingFace
- **Database**: SQLite (Local DB)
- **Observability**: logging. Logs are not sent to any external service as of now.
- **UI**: Streamlit
- **Evals**: Choose Deepeval if nothing is specified.

### Common Development and Evaluation Patterns
- **Dependency Management**: Use `pip` and `requirements.txt` for managing dependencies. Avoid using `conda` or other package managers.
- **Versioning**: Use semantic versioning for the features under each framework. Update the version in the `changelog.md` file in the root of the repo for any new feature or significant change.
- **Agent Design**: When writing Agents or multi-agent setups, follow the framework-specific guidelines and best practices.
  - Framework directories are intentionally hyphenated e.g. `agentic-langgraph` or `agentic-maf`. Never create or import `src.langgraph` or `src.maf`; use the existing dynamic-loading pattern in `src/main.py` and `tests/conftest.py`.
  - If not specified in prompt, ask the user following questions before designing the Agent:
    1. What is the goal of the Agent?
    2. What are the inputs and outputs of the Agent?
    3. What are the constraints and limitations of the Agent?
    4. Which personas or roles or business processes will use the Agent?
  - Ensure that the multi-agent setup is modular. Preferably create a class inside `src/<framework>/agent.py` that encapsulates the multi-agent setup and can be consumed by calling the instance inside an API or a script or a notebook.
- **Creating and using tools**: Package external dependencies and deterministic functions as tools for Agents. 
  - **Examples**: Running SQL queries on the SQLite database, performing calculations (eg revenue, profit, engagement conversion rate etc.), verifying SQL query in syntactic way, querying vector index etc.
  - **Never** package non-deterministic functions, decision-making, sub-agent routing, hand-off as tools for Agents.
  - **Use** framework-specific syntaxes to create tools, preferably in `src/<framework>/tools.py` file.
- **Reusable Components**: Create reusable components (not related to tools for Agents) for common tasks under `src/utils` folder and import the relevant methods to scripts inside `src/<framework>/utils` folder. These utilities should be designed in a way that they can be shared across the project, ideally for both agent development and evaluation, and different frameworks (langchain and MAF). Primary purpose is to promote code reuse across the repo and maintainability.
  -  Make sure that you are not importing any framework eg langchain or MAF specific code inside `src/utils/` folder.
  - Use separate of concerns to create appropriate utility functions/script eg `db.py` to handle db related functions etc.
- **Adding skills**: If you add a new agent skill, add it under `src/skills` folder. Skills should be framework-agnostic as much as possible to promote reusability. Update the `design.md` in the relevant framework folder(s) to reflect the addition of the new skill and its usage. The skill should be designed to be framework-agnostic, and should contain only the specific logic, not how or when to call it. The calling logic should be in the framework-specific code.
- **Evaluation Metrics**: Implement evaluation metrics that are relevant to the RAG application.
- **Design Documents**: Each framework-related folder gets a `design.md`. For any new feature or significant change, modify the `design.md` and maintain a decision log to track the changes.
- **Add tests**: For any new feature or significant change, add tests to the `tests/<framework>/` directory.
- **Always keep imports at the top**: Avoid optional imports and imports within methods.
  - If a new library is needed, it should be added to `requirements.txt` and installed in the virtual environment.
  - Write imports only in the top-level scope of the module, not inside functions or classes.
