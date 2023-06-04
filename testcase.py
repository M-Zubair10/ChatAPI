import requests

payload = {
    'prompt': "Generalize the sentence given below in one word\n\n\n\n\n\nThere is a basket of strawberries in the room",
}

host = 'http://127.0.0.1:5005'

response = requests.get(f"{host}/poe", json=payload)

print("Response:", response.content.decode("utf-8"))
