# Streamlit RAG Application

This project is a Streamlit application that utilizes Retrieval-Augmented Generation (RAG) to process user queries and provide responses based on a pre-trained model.

## Project Structure

```
streamlit-rag-app
├── src
│   ├── app.py          # Main entry point for the Streamlit application
│   ├── rag_llm.py      # Contains the rag_llm_call function and logic for processing queries
│   └── utils
│       └── __init__.py # Placeholder for utility functions
├── requirements.txt     # Lists the dependencies required for the project
└── README.md            # Documentation for the project
```

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd streamlit-rag-app
   ```

2. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Run the Streamlit application:**
   ```bash
   streamlit run src/app.py
   ```

2. **Open your web browser and navigate to:**
   ```
   http://localhost:8501
   ```

3. **Input your query in the provided text box and submit to receive a response.**

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.