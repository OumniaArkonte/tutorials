import requests

BASE_URL = "http://127.0.0.1:8000"

def test_procure():
    url = f"{BASE_URL}/procure"
    # location en query string
    params = {"location": "Madrid, Spain"}
    # product_list dans le body en liste brute
    payload = ["Office Chairs", "MacBooks", "Whiteboards"]

    response = requests.post(url, params=params, json=payload)
    print("=== /procure response ===")
    print("Status:", response.status_code)
    try:
        print("JSON:", response.json())
    except:
        print("Texte brut:", response.text)


def test_csv():
    url = f"{BASE_URL}/csv"
    response = requests.get(url)
    print("\n=== /csv response ===")
    print("Status:", response.status_code)

    if response.status_code == 200:
        with open("downloaded_data.csv", "wb") as f:
            f.write(response.content)
        print(" CSV téléchargé sous 'downloaded_data.csv'")
    else:
        print(" CSV non trouvé")


if __name__ == "__main__":
    test_procure()
    test_csv()
