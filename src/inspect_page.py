import requests
from bs4 import BeautifulSoup

url = "https://www.du.ac.bd/"

response = requests.get(
    url,
    timeout=20,
    headers={"User-Agent": "Mozilla/5.0"}
)

print("Status:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")

# =====================================================
# HEADINGS
# =====================================================

print("\nHEADINGS")
print("=" * 80)

for i, heading in enumerate(
    soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]),
    start=1
):
    text = heading.get_text(" ", strip=True)

    print(
        f"{i:03d} | {heading.name.upper():2} | {text[:150]}"
    )


# =====================================================
# GENERIC LINKS
# =====================================================

generic = {
    "click here",
    "read more",
    "more",
    "here",
    "learn more",
    "details",
    "link"
}

print("\nGENERIC LINKS")
print("=" * 80)

count = 0

for link in soup.find_all("a"):

    text = link.get_text(" ", strip=True)

    if text.lower() in generic:

        count += 1

        print(
            f"{count:03d} | {repr(text)} | {link.get('href')}"
        )


# =====================================================
# EMPTY LINKS
# =====================================================

print("\nEMPTY LINKS")
print("=" * 80)

count = 0

for link in soup.find_all("a"):

    text = link.get_text(" ", strip=True)

    if not text:

        count += 1

        print(
            f"{count:03d} | href={link.get('href')} "
            f"| aria-label={link.get('aria-label')} "
            f"| title={link.get('title')}"
        )

print("\nTotal empty links:", count)
print("Total generic links:", len([
    a for a in soup.find_all("a")
    if a.get_text(" ", strip=True).lower() in generic
]))
