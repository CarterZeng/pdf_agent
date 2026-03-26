import requests

response = requests.post("https://noneastern-cindi-nonvocalic.ngrok-free.dev/chat", json={"prompt": "What is N-gram?"})
print(response.json())