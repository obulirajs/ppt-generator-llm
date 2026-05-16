from utils.llm_service import generate_presentation_structure, check_ollama_connection, get_available_models

# Check connection
is_running, error = check_ollama_connection()
print(f"Ollama running: {is_running}")
if error:
    print(f"Error: {error}")

# List models
models = get_available_models()
print(f"Available models: {models}")

# Test generation
test_content = """
Artificial Intelligence is transforming modern business. 
Companies are using AI for automation, customer service, and data analysis.
Machine learning models can predict customer behavior and optimize operations.
Natural language processing enables chatbots and content generation.
The future of AI includes more sophisticated reasoning and decision-making capabilities.
"""

try:
    structure = generate_presentation_structure(test_content, "llama3.2")
    print("\n✓ Generated structure:")
    import json
    print(json.dumps(structure, indent=2))
except Exception as e:
    print(f"Error: {e}")