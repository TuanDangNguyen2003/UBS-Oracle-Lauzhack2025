# file: llm_config.py
from pyagentspec.llms import OllamaConfig

llm_config = OllamaConfig(
    name="ollama-llm",
    model_id="gpt-oss:20b",     # from `ollama list`
    url="http://localhost:11434"  # Ollama server
)
'''# file: llm_config.py
from pyagentspec.llms import OpenAiConfig


llm_config = OpenAiConfig(
    name="gpt-oss-20b-local",
    model_id="gpt-oss-20b",       # or whichever GPT-OSS model you installed
    description="Local GPT-OSS 20B model running on http://127.0.0.1:8080/v1",
)'''



