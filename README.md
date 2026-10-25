# Backbone

An AI tutoring project that retrieves course material to help answer student questions.

## Projects

- **[backbone-ui](backbone-ui/)**: Web interface and FastAPI/Streamlit application, retrieval processing, and local Ollama integration. See its [setup instructions](backbone-ui/README.md).
- **[backbone-i2p](backbone-i2p/)**: Backend project scaffold, course configuration schemas, and ingestion manifests.

Both projects are collected here with their commit histories and contributor attribution. The published history excludes waitlist signup records, course textbooks and slides, research PDFs, generated search indexes, and Python build artifacts. The original local project folders are unchanged.

## Getting started

Start with the [UI setup guide](backbone-ui/README.md). It covers Python dependencies, Ollama, and running the FastAPI or Streamlit interface.

The backend scaffold has its own [Python project configuration](backbone-i2p/pyproject.toml); it does not yet provide a complete standalone server.

## Course materials

Supply your own permitted course documents locally and run the ingestion scripts to generate retrieval data. Textbooks, slides, research papers, and prebuilt search indexes are not distributed in this repository. The tutoring features require these local inputs.
