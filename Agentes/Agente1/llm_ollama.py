from llm_controller import LLMController
import requests

class LLMOllama(LLMController):
    # La url tiene que ser al metodo .../chat de la API de OLLAMA

    def __init__(self, url, model):
        self.url = url
        self.model = model

    def completion(self, prompt):
        messages = [
            {"role" : "user", "content" : prompt}
        ]

        payload = {
            "model" : self.model,
            "messages" : messages,
            "stream" : False
        }

        response = requests.post(url = self.url, json = payload)
        return response.json()["message"]["content"]
    