from enum import Enum
import requests
import dspy
import os
import pickle
import faiss

LOCAL_SERVER_OLLAMA = os.getenv('LOCAL_OLLAMA_SERVER')
OLLAMA_PUBLIC_KEY = os.getenv('OLLAMA_PUBLIC_KEY')

# Initialize the language model
lm = dspy.LM(
        'ollama_chat/deepseek-r1:1.5b', 
        api_base=LOCAL_SERVER_OLLAMA, 
        api_key=OLLAMA_PUBLIC_KEY,
        cahce=False
        )
dspy.configure(lm=lm)

#ISA, Datapath, Control Path, Interrupts, Performance, Pipelining, Hazards, Scheduling, Virtual Memory, Memory Heirarchy, Parallel Systems, Networking
class DataSourceType(Enum):
    ISA = 1
    DATAPATH = 2
    CONTROL_PATH = 3
    INTERRUPTS = 4
    PERFORMANCE = 5
    PIPELINING = 6
    HAZARDS = 7
    SCHEDULING = 8
    VIRTUAL_MEMORY = 9
    MEMORY_HIERARCHY = 10
    PARALLEL_SYSTEMS = 11
    NETWORKING = 12
    DISK_SCHEDULING = 13
    FILE_SYSTEMS = 14

class ClassifySignature(dspy.Signature):
    """Classify the given information into one of the provided categories."""
    information = dspy.InputField()
    labels = dspy.InputField()
    prompt = dspy.InputField()
    category: str = dspy.OutputField(desc="Only one category name and it has to be exact same name as the input labels. Utilize the prompt given the slide name to do so.")

def build_prompt_classification(query, labels):
    labels_str = ", ".join(labels)
    prompt = f"""You are a helpful assistant. Given the slide name, please classify the slide into one of the following categories: {labels_str}. Slide Name: {query}."""
    return prompt

def classify_information(information: str, model="mistral") -> str:
    labels = [label.name for label in DataSourceType]
    labels_str = ", ".join(labels)
    # Set up the dspy predictor (uses OpenAI by default, but you can configure for local models)
    predictor = dspy.Predict(ClassifySignature)
    result = predictor(
        information=information,
        labels=labels_str,
        prompt=build_prompt_classification(information, labels)
    )
    print("Category: " + result.category)
    return result.category
# classify_information("This slide explains the concept of pipelining in computer architecture, detailing how multiple instruction phases can overlap to improve performance.", model="mistral")  # Example usage

# with open("../../data_sources/chunk_map.pkl", "rb") as f:
#     chunk_map = pickle.load(f)

# # Print the entire chunk_map (may be large!)
# for idx, entry in chunk_map.items():
#     print(f"Index: {idx}")
#     if ("metadata" not in entry):
#         print(entry)

#     print("-" * 40)