import requests
from bs4 import BeautifulSoup


def scan_page(url):
    result = {
        "url": url,

        # -------------------------
        # Images
        # -------------------------
        "total_images": 0,
        "images_missing_alt": 0,
        "images_empty_alt": 0,
        "images_with_alt": 0,
        "images_with_role_presentation": 0,
        "image_issues": [],

        # -------------------------
        # Headings
        # -------------------------
        "total_headings": 0,
        "h1_count": 0,
        "heading_order_issues": 0,
        "heading_issues": [],

        # -------------------------
        # Links
        # -------------------------
        "total_links": 0,
        "empty_link_text": 0,
        "generic_link_text": 0,
        "links_with_aria_label": 0,
        "link_issues": [],

        # -------------------------
        # Forms
        # -------------------------
        "form_controls": 0,
        "unlabeled_controls": 0,
        "form_issues": [],

        # -------------------------
        # Metadata
        # -------------------------
        "has_title": 0,
        "has_lang": 0,

        # -------------------------
        # Technical
        # -------------------------
        "status_code": None,
        "error": ""
    }

    try:
        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        result["status_code"] = response.status_code

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # =====================================================
        # 1. IMAGE ACCESSIBILITY
        # =====================================================

        images = soup.find_all("img")

        result["total_images"] = len(images)

        for index, img in enumerate(images, start=1):

            src = img.get("src", "")
            alt = img.get("alt")
            role = img.get("role", "").lower()

            # Role presentation
            if role == "presentation":
                result["images_with_role_presentation"] += 1

            # Missing alt attribute
            if not img.has_attr("alt"):

                result["images_missing_alt"] += 1

                result["image_issues"].append({
                    "element": "img",
                    "index": index,
                    "src": src,
                    "alt": None,
                    "issue": "missing_alt",
                    "severity": "high",
                    "reason": "Image does not have an alt attribute."
                })

            # Empty alt attribute
            elif alt.strip() == "":

                result["images_empty_alt"] += 1

                result["image_issues"].append({
                    "element": "img",
                    "index": index,
                    "src": src,
                    "alt": "",
                    "issue": "empty_alt",
                    "severity": "medium",
                    "reason": "Image has an empty alt attribute."
                })

            # Non-empty alt
            else:

                result["images_with_alt"] += 1

        # =====================================================
        # 2. HEADING ACCESSIBILITY
        # =====================================================

        headings = soup.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6"]
        )

        result["total_headings"] = len(headings)

        result["h1_count"] = len(
            soup.find_all("h1")
        )

        # No H1
        if result["h1_count"] == 0:

            result["heading_issues"].append({
                "element": "heading",
                "tag": "h1",
                "text": "",
                "issue": "missing_h1",
                "severity": "high",
                "reason": "Page does not contain an H1 heading."
            })

        # Multiple H1
        elif result["h1_count"] > 1:

            result["heading_issues"].append({
                "element": "heading",
                "tag": "h1",
                "text": "",
                "issue": "multiple_h1",
                "severity": "medium",
                "reason": "Page contains multiple H1 headings."
            })

        previous_level = 0

        for index, heading in enumerate(headings, start=1):

            current_level = int(
                heading.name[1]
            )

            text = heading.get_text(
                " ",
                strip=True
            )

            if previous_level != 0:

                if current_level > previous_level + 1:

                    result["heading_order_issues"] += 1

                    result["heading_issues"].append({
                        "element": "heading",
                        "index": index,
                        "tag": heading.name,
                        "text": text,
                        "issue": "heading_order",
                        "severity": "medium",
                        "reason": (
                            f"Heading level jumps from H{previous_level} "
                            f"to H{current_level}."
                        )
                    })

            # Empty heading
            if not text:

                result["heading_issues"].append({
                    "element": "heading",
                    "index": index,
                    "tag": heading.name,
                    "text": "",
                    "issue": "empty_heading",
                    "severity": "medium",
                    "reason": "Heading has no accessible text."
                })

            previous_level = current_level
            
        # =====================================================
        # 3. LINK ACCESSIBILITY
        # =====================================================

        links = soup.find_all("a")

        result["total_links"] = len(links)

        generic_text = {
            "click here",
            "read more",
            "more",
            "here",
            "learn more",
            "details",
            "link"
        }

        for index, link in enumerate(links, start=1):

            text = link.get_text(
                " ",
                strip=True
            )

            text_lower = text.lower()

            aria_label = link.get("aria-label")
            title = link.get("title")
            href = link.get("href")

            has_accessible_name = False
            name_source = None

            # -------------------------------------------------
            # 1. Visible text
            # -------------------------------------------------

            if text:

                has_accessible_name = True
                name_source = "visible_text"

            # -------------------------------------------------
            # 2. aria-label
            # -------------------------------------------------

            elif aria_label:

                has_accessible_name = True
                name_source = "aria_label"

                result["links_with_aria_label"] += 1

            # -------------------------------------------------
            # 3. title
            # -------------------------------------------------

            elif title:

                has_accessible_name = True
                name_source = "title"

            # -------------------------------------------------
            # 4. Image alt
            # -------------------------------------------------

            else:

                images_inside = link.find_all("img")

                for image in images_inside:

                    alt = image.get("alt")

                    if alt and alt.strip():

                        has_accessible_name = True
                        name_source = "image_alt"
                        break

            # -------------------------------------------------
            # Empty / inaccessible link
            # -------------------------------------------------

            if not has_accessible_name:

                result["empty_link_text"] += 1

                result["link_issues"].append({

                    "element": "a",
                    "index": index,
                    "text": text,
                    "href": href,
                    "aria_label": aria_label,
                    "title": title,
                    "accessible_name": "",
                    "name_source": "none",
                    "issue": "empty_link_text",
                    "severity": "high",
                    "reason": (
                        "Link has no accessible name. "
                        "Add meaningful link text, "
                        "aria-label, or image alt text."
                    )

                })

            # -------------------------------------------------
            # Generic link text
            # -------------------------------------------------

            elif text_lower in generic_text:

                result["generic_link_text"] += 1

                result["link_issues"].append({

                    "element": "a",
                    "index": index,
                    "text": text,
                    "href": href,
                    "aria_label": aria_label,
                    "title": title,
                    "accessible_name": text,
                    "name_source": name_source,
                    "issue": "generic_link_text",
                    "severity": "medium",
                    "reason": (
                        "Link text is generic and does not "
                        "clearly identify the destination."
                    )

                })

        # =====================================================
        # 5. PAGE TITLE
        # =====================================================

        title = soup.find("title")

        if title and title.get_text(strip=True):

            result["has_title"] = 1

        # =====================================================
        # 6. LANGUAGE ATTRIBUTE
        # =====================================================

        html = soup.find("html")

        if html and html.get("lang"):

            result["has_lang"] = 1

    except Exception as e:

        result["error"] = str(e)

    return result


# =============================================================
# TEST
# =============================================================

if __name__ == "__main__":

    url = "https://bau.edu.bd/"

    result = scan_page(url)

    print()
    print("Accessibility Scan")
    print("=" * 60)

    for key, value in result.items():

        if key in [
            "image_issues",
            "heading_issues",
            "link_issues",
            "form_issues"
        ]:
            print(f"{key}: {len(value)}")

        else:
            print(f"{key}: {value}")
