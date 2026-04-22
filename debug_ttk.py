import requests

response = requests.post("http://localhost:5050/annotate", json={"text": "John arrived in Tokyo on July 23.", "dct": "2023-01-01"})
print(response.status_code)
print(response.text)
