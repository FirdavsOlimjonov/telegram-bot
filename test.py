import requests
import certifi

url = "https://api.telegram.org"
try:
    response = requests.get(url, verify=certifi.where())
    print("SSL is working. Status Code:", response.status_code)
except requests.exceptions.SSLError as e:
    print("SSL Error:", e)
except Exception as e:
    print("Other Error:", e)
