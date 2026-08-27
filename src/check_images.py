import requests
from bs4 import BeautifulSoup

url = "https://bau.edu.bd/"

response = requests.get(
    url,
    timeout=20,
    headers={"User-Agent": "Mozilla/5.0"}
)

soup = BeautifulSoup(response.text, "html.parser")

images = soup.find_all("img")

print("Total images:", len(images))
print("\nImage details")
print("=" * 80)

for i, img in enumerate(images, start=1):
    src = img.get("src", "")
    alt = img.get("alt", None)

    print(f"\nImage {i}")
    print("SRC:", src)
    print("ALT:", repr(alt))
