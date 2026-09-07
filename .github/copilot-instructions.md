# RAG-with-evals

This is a repo to contain code for various RAG use cases, with a focus on evaluation of the output.

## Folder Structure
### Key Directories
- `src/`: Contains the main source code for the RAG samples.
  - `notebooks/`: Jupyter notebooks where I experiment. Do not refer to these unless explicitely sent as part of a request.
  - `local_db/`: Contains schema and seeding for local SQLite databases as source of truth and the db.
  - `langgraph/`: Contains code written on langchain-langgraph ecosystem.
  - `maf/`: Contains code written on Microsoft Agent Framework ecosystem.
  - `evals/`: Contains code for evaluation of RAG outputs, including metrics and evaluation scripts.
    - `ground_truth/`: Contains ground truth data generator and seeding for evaluation.
  - `utils/`: Contains utility functions and shared components that can be used across different frameworks code.
  - `skills/`: Contains reusable skills that can be used across different frameworks code.
  - `prompts/`: Contains prompts for LLMs in .txt format. The idea is to re-use the same prompt in different frameworks. The prompt should be framework-agnostic and should not contain any framework-specific syntax. Preferably in `.md` format.
- `tests/`: Comprehensive test suite. Separate the tests for each framework under `tests/langgraph` and `tests/maf`.

### Technology Stack
Use the following technologies in this repo. If you need to add another tech, ask first.
- **Language**: Python 3.11+
- **Framework**: Langchain, LangGraph, Microsoft Agent Framework, FastAPI
- **AI**: Azure Foundry and Azure OpenAI, HuggingFace
- **Database**: SQLite (Local DB)
- **Observability**: logging. Logs are not sent to any external service as of now.
- **UI**: Streamlit

### Common Development and Evaluation Patterns
- **Dependency Management**: Use `pip` and `requirements.txt` for managing dependencies. Avoid using `conda` or other package managers.
- **Versioning**: Use semantic versioning for the features under each framework. Update the version in the `changelog.md` file in the root of the repo for any new feature or significant change.
- **Creating and using tools**: Package external dependencies and deterministic functions as tools for Agents. 
  - **Examples**: Running SQL queries on the SQLite database, performing calculations (eg revenue, profit, engagement conversion rate etc.), verifying SQL query in syntactic way, querying vector index etc.
  - **Never** package non-deterministic functions, decision-making, routing, hand-off as tools for Agents.
  - **Use** framework-specific syntaxes to create tools, preferably in `src/<framework>/tools.py` file.
- **Reusable Components**: Create reusable components (not related to tools for Agents) for common tasks under `src/utils` folder that can be shared across the project and different frameworks (langchain and MAF).
- **Separation of Concerns**: Keep the code modular and organized. Do not mix multiple functionalities in a single method or class. Add clear docstrings and comments to explain the purpose of each component.
- **Adding skills**: If you add a new skill, add it under `src/skills` folder. Skills should be framework-agnostic as much as possible. Update the `design.md` in the relevant framework folder(s) to reflect the addition of the new skill and its usage. The skill should be designed to be framework-agnostic, and should contain only the specific logic, not how or when to call it. The calling logic should be in the framework-specific code.
- **Evaluation Metrics**: Implement evaluation metrics that are relevant to the RAG application.
- **Design Documents**: Each framework-related folder gets a `design.md`. For any new feature or significant change, modify the `design.md` and maintain a decision log to track the changes.
- **Add tests**: For any new feature or significant change, add tests to the `tests/<framework>` directory. Ensure that the tests cover >80% of the code and edge cases.
- **Using imports**: Avoid optional imports. If a library is needed, it should be added to `requirements.txt` and installed in the virtual environment. Use imports only in the top-level scope of the module, not inside functions or classes.
