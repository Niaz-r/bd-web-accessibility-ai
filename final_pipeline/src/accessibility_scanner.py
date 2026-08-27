import re
import requests
from bs4 import BeautifulSoup


# =============================================================
# HELPERS
# =============================================================

def compact_html(element, max_length=600):
    """
    Return a compact HTML representation of an element.
    """

    if element is None:
        return ""

    html = str(element)

    html = " ".join(
        html.split()
    )

    if len(html) > max_length:
        html = html[:max_length] + "..."

    return html


def build_css_selector(element):
    """
    Build a CSS-like selector for a BeautifulSoup element.

    This is intended for evidence/location reporting.
    It may not be identical to selectors produced by
    browser tools such as axe-core.
    """

    if element is None:
        return ""

    parts = []

    current = element

    max_depth = 8
    depth = 0

    while (
        current is not None
        and getattr(current, "name", None)
        and current.name != "[document]"
        and depth < max_depth
    ):

        name = current.name

        element_id = current.get("id")

        classes = current.get(
            "class",
            []
        )

        # -----------------------------------------------------
        # ID selector
        # -----------------------------------------------------

        if element_id:

            part = (
                f"{name}#{element_id}"
            )

            parts.insert(
                0,
                part
            )

            break

        # -----------------------------------------------------
        # Tag
        # -----------------------------------------------------

        part = name

        # -----------------------------------------------------
        # Classes
        # -----------------------------------------------------

        if classes:

            usable_classes = [
                str(cls)
                for cls in classes[:2]
                if str(cls).strip()
            ]

            if usable_classes:

                part += "".join(
                    f".{cls}"
                    for cls
                    in usable_classes
                )

        # -----------------------------------------------------
        # nth-of-type
        # -----------------------------------------------------

        parent = current.parent

        if (
            parent is not None
            and getattr(
                parent,
                "find_all",
                None
            )
        ):

            same_tag_siblings = (
                parent.find_all(
                    name,
                    recursive=False
                )
            )

            if len(
                same_tag_siblings
            ) > 1:

                try:

                    position = (
                        same_tag_siblings.index(
                            current
                        )
                        + 1
                    )

                    part += (
                        f":nth-of-type("
                        f"{position}"
                        f")"
                    )

                except ValueError:
                    pass

        parts.insert(
            0,
            part
        )

        current = parent

        depth += 1

    return " > ".join(
        parts
    )


def element_metadata(element):
    """
    Return element evidence/location metadata.
    """

    if element is None:

        return {
            "selector": "",
            "html_snippet": "",
            "element_id": "",
            "element_classes": ""
        }

    classes = element.get(
        "class",
        []
    )

    return {

        "selector":
            build_css_selector(
                element
            ),

        "html_snippet":
            compact_html(
                element
            ),

        "element_id":
            element.get(
                "id",
                ""
            ),

        "element_classes":
            " ".join(
                str(cls)
                for cls
                in classes
            )
    }

# =============================================================
# ALT TEXT QUALITY HELPERS
# =============================================================

GENERIC_ALT_TEXTS = {

    "image",
    "img",

    "photo",
    "picture",
    "pic",

    "thumbnail",
    "thumb",

    "image here",
    "photo here",

    "news image",
    "news photo",

    "event image",
    "event photo",

    "banner image",
    "banner photo",

    "slider image",
    "slider photo",

    "slide image",
    "slide photo",

    "featured image",
    "featured photo",

    "default image",
    "default photo",

    "placeholder image",
    "placeholder photo",

    "placeholder",
    "default",

    "sample",
    "test",

    "untitled",

    "no image",
    "no-image",
    "no photo",
    "no-photo"
}


def normalize_alt_text(value):
    """
    Normalize alt text for conservative quality checks.
    """

    if value is None:
        return ""

    value = str(
        value
    ).strip().lower()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value


def detect_non_descriptive_alt(alt_text):
    """
    Detect obvious generic, placeholder, filename-like,
    or camera-generated alt text.

    Returns:
        (True, reason)
        or
        (False, "")
    """

    alt = normalize_alt_text(
        alt_text
    )

    if not alt:
        return (
            False,
            ""
        )

    # ---------------------------------------------------------
    # 1. Exact generic values
    # ---------------------------------------------------------

    if alt in GENERIC_ALT_TEXTS:

        return (
            True,
            "Alt text is generic and does not describe "
            "the image's content or purpose."
        )

    # ---------------------------------------------------------
    # 2. Generic word + number
    #
    # Examples:
    # image1
    # image_01
    # photo-2
    # thumbnail 5
    # ---------------------------------------------------------

    generic_number_pattern = (
        r"^(?:"
        r"image|img|photo|picture|pic|"
        r"thumbnail|thumb|banner|slide"
        r")"
        r"[\s_-]*"
        r"\d+$"
    )

    if re.fullmatch(
        generic_number_pattern,
        alt
    ):

        return (
            True,
            "Alt text appears to be a generic placeholder "
            "combined with a number."
        )

    # ---------------------------------------------------------
    # 3. Filename used directly as alt
    #
    # Examples:
    # image.jpg
    # banner_01.png
    # event-photo.webp
    # ---------------------------------------------------------

    filename_pattern = (
        r"^[^<>]+"
        r"\.(?:"
        r"jpg|jpeg|png|gif|webp|svg|avif|bmp"
        r")$"
    )

    if re.fullmatch(
        filename_pattern,
        alt
    ):

        return (
            True,
            "Alt text appears to be an image filename "
            "rather than a meaningful description."
        )

    # ---------------------------------------------------------
    # 4. Common camera/system-generated names
    #
    # Examples:
    # IMG_1234
    # DSC_0098
    # DSCF1234
    # Screenshot_2026-08-20
    # ---------------------------------------------------------

    camera_pattern = (
        r"^(?:"
        r"img|dsc|dscf|dcim|pxl"
        r")"
        r"[\s_-]*"
        r"\d+"
        r"(?:[\s_-]*\d+)*$"
    )

    if re.fullmatch(
        camera_pattern,
        alt
    ):

        return (
            True,
            "Alt text appears to be a camera-generated "
            "file identifier."
        )

    screenshot_pattern = (
        r"^screenshot"
        r"(?:[\s_-].*)?$"
    )

    if re.fullmatch(
        screenshot_pattern,
        alt
    ):

        return (
            True,
            "Alt text appears to be a screenshot filename "
            "or generic screenshot label."
        )

    return (
        False,
        ""
    )
# =============================================================
# MAIN SCANNER
# =============================================================

def scan_page(url):

    result = {

        "url": url,

        # -----------------------------------------------------
        # Images
        # -----------------------------------------------------

        "total_images": 0,

        "images_missing_alt": 0,

        "images_empty_alt": 0,

        "images_non_descriptive_alt": 0,

        "images_with_alt": 0,

        "images_with_role_presentation": 0,

        "image_issues": [],

        # -----------------------------------------------------
        # Headings
        # -----------------------------------------------------

        "total_headings": 0,

        "h1_count": 0,

        "heading_order_issues": 0,

        "heading_issues": [],

        # -----------------------------------------------------
        # Links
        # -----------------------------------------------------

        "total_links": 0,

        "empty_link_text": 0,

        "generic_link_text": 0,

        "links_with_aria_label": 0,

        "link_issues": [],

        # -----------------------------------------------------
        # Forms
        # -----------------------------------------------------

        "form_controls": 0,

        "unlabeled_controls": 0,

        "form_issues": [],

        # -----------------------------------------------------
        # Metadata
        # -----------------------------------------------------

        "has_title": 0,

        "has_lang": 0,

        # -----------------------------------------------------
        # Technical
        # -----------------------------------------------------

        "status_code": None,

        "error": ""
    }

    try:

        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent":
                    "Mozilla/5.0"
            }
        )

        result[
            "status_code"
        ] = response.status_code

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # =====================================================
        # 1. IMAGE ACCESSIBILITY
        # =====================================================

        images = soup.find_all(
            "img"
        )

        result[
            "total_images"
        ] = len(images)

        for index, img in enumerate(
            images,
            start=1
        ):

            src = img.get(
                "src",
                ""
            )

            alt = img.get(
                "alt"
            )

            role = img.get(
                "role",
                ""
            ).lower()

            metadata = (
                element_metadata(
                    img
                )
            )

            # -------------------------------------------------
            # Role presentation
            # -------------------------------------------------

            if role == "presentation":

                result[
                    "images_with_role_presentation"
                ] += 1

            # -------------------------------------------------
            # Missing alt
            # -------------------------------------------------

            if not img.has_attr(
                "alt"
            ):

                result[
                    "images_missing_alt"
                ] += 1

                result[
                    "image_issues"
                ].append(
                    {
                        "element":
                            "img",

                        "index":
                            index,

                        "src":
                            src,

                        "alt":
                            None,

                        "selector":
                            metadata[
                                "selector"
                            ],

                        "html_snippet":
                            metadata[
                                "html_snippet"
                            ],

                        "element_id":
                            metadata[
                                "element_id"
                            ],

                        "element_classes":
                            metadata[
                                "element_classes"
                            ],

                        "issue":
                            "missing_alt",

                        "severity":
                            "high",

                        "reason":
                            (
                                "Image does not have "
                                "an alt attribute."
                            )
                    }
                )

            # -------------------------------------------------
            # Empty alt
            # -------------------------------------------------

            elif (
                alt is not None
                and alt.strip() == ""
            ):

                result[
                    "images_empty_alt"
                ] += 1

                result[
                    "image_issues"
                ].append(
                    {
                        "element":
                            "img",

                        "index":
                            index,

                        "src":
                            src,

                        "alt":
                            "",

                        "selector":
                            metadata[
                                "selector"
                            ],

                        "html_snippet":
                            metadata[
                                "html_snippet"
                            ],

                        "element_id":
                            metadata[
                                "element_id"
                            ],

                        "element_classes":
                            metadata[
                                "element_classes"
                            ],

                        "issue":
                            "empty_alt",

                        "severity":
                            "medium",

                        "reason":
                            (
                                "Image has an empty "
                                "alt attribute."
                            )
                    }
                )

            # -------------------------------------------------
            # Non-empty alt
            # -------------------------------------------------

            else:

                result[
                    "images_with_alt"
                ] += 1

                # =============================================
                # NON-DESCRIPTIVE ALT TEXT
                # =============================================

                is_non_descriptive, quality_reason = (
                    detect_non_descriptive_alt(
                        alt
                    )
                )

                if is_non_descriptive:

                    result[
                        "images_non_descriptive_alt"
                    ] += 1

                    result[
                        "image_issues"
                    ].append(
                        {
                            "element":
                                "img",

                            "index":
                                index,

                            "src":
                                src,

                            "alt":
                                alt,

                            "selector":
                                metadata[
                                    "selector"
                                ],

                            "html_snippet":
                                metadata[
                                    "html_snippet"
                                ],

                            "element_id":
                                metadata[
                                    "element_id"
                                ],

                            "element_classes":
                                metadata[
                                    "element_classes"
                                ],

                            "issue":
                                "non_descriptive_alt",

                            "severity":
                                "medium",

                            "reason":
                                quality_reason
                        }
                    )

        # =====================================================
        # 2. HEADING ACCESSIBILITY
        # =====================================================

        headings = soup.find_all(
            [
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6"
            ]
        )

        result[
            "total_headings"
        ] = len(headings)

        result[
            "h1_count"
        ] = len(
            soup.find_all(
                "h1"
            )
        )

        # -----------------------------------------------------
        # Missing H1
        # -----------------------------------------------------

        if result[
            "h1_count"
        ] == 0:

            result[
                "heading_issues"
            ].append(
                {
                    "element":
                        "heading",

                    "tag":
                        "h1",

                    "text":
                        "",

                    "selector":
                        "",

                    "html_snippet":
                        "",

                    "element_id":
                        "",

                    "element_classes":
                        "",

                    "issue":
                        "missing_h1",

                    "severity":
                        "high",

                    "reason":
                        (
                            "Page does not contain "
                            "an H1 heading."
                        )
                }
            )

        # -----------------------------------------------------
        # Multiple H1
        # -----------------------------------------------------

        elif result[
            "h1_count"
        ] > 1:

            result[
                "heading_issues"
            ].append(
                {
                    "element":
                        "heading",

                    "tag":
                        "h1",

                    "text":
                        "",

                    "selector":
                        "",

                    "html_snippet":
                        "",

                    "element_id":
                        "",

                    "element_classes":
                        "",

                    "issue":
                        "multiple_h1",

                    "severity":
                        "medium",

                    "reason":
                        (
                            "Page contains multiple "
                            "H1 headings."
                        )
                }
            )

        previous_level = 0

        for index, heading in enumerate(
            headings,
            start=1
        ):

            current_level = int(
                heading.name[1]
            )

            text = heading.get_text(
                " ",
                strip=True
            )

            metadata = (
                element_metadata(
                    heading
                )
            )

            # -------------------------------------------------
            # Heading order
            # -------------------------------------------------

            if previous_level != 0:

                if (
                    current_level
                    >
                    previous_level + 1
                ):

                    result[
                        "heading_order_issues"
                    ] += 1

                    result[
                        "heading_issues"
                    ].append(
                        {
                            "element":
                                "heading",

                            "index":
                                index,

                            "tag":
                                heading.name,

                            "text":
                                text,

                            "selector":
                                metadata[
                                    "selector"
                                ],

                            "html_snippet":
                                metadata[
                                    "html_snippet"
                                ],

                            "element_id":
                                metadata[
                                    "element_id"
                                ],

                            "element_classes":
                                metadata[
                                    "element_classes"
                                ],

                            "issue":
                                "heading_order",

                            "severity":
                                "medium",

                            "reason":
                                (
                                    f"Heading level jumps "
                                    f"from H{previous_level} "
                                    f"to H{current_level}."
                                )
                        }
                    )

            # -------------------------------------------------
            # Empty heading
            # -------------------------------------------------

            if not text:

                result[
                    "heading_issues"
                ].append(
                    {
                        "element":
                            "heading",

                        "index":
                            index,

                        "tag":
                            heading.name,

                        "text":
                            "",

                        "selector":
                            metadata[
                                "selector"
                            ],

                        "html_snippet":
                            metadata[
                                "html_snippet"
                            ],

                        "element_id":
                            metadata[
                                "element_id"
                            ],

                        "element_classes":
                            metadata[
                                "element_classes"
                            ],

                        "issue":
                            "empty_heading",

                        "severity":
                            "medium",

                        "reason":
                            (
                                "Heading has no "
                                "accessible text."
                            )
                    }
                )

            previous_level = (
                current_level
            )

        # =====================================================
        # 3. LINK ACCESSIBILITY
        # =====================================================

        links = soup.find_all(
            "a"
        )

        result[
            "total_links"
        ] = len(links)

        generic_text = {
            "click here",
            "read more",
            "more",
            "here",
            "learn more",
            "details",
            "link"
        }

        for index, link in enumerate(
            links,
            start=1
        ):

            text = link.get_text(
                " ",
                strip=True
            )

            text_lower = (
                text.lower()
            )

            aria_label = link.get(
                "aria-label"
            )

            title = link.get(
                "title"
            )

            href = link.get(
                "href"
            )

            metadata = (
                element_metadata(
                    link
                )
            )

            has_accessible_name = (
                False
            )

            name_source = None

            accessible_name = ""

            # -------------------------------------------------
            # 1. Visible text
            # -------------------------------------------------

            if text:

                has_accessible_name = (
                    True
                )

                name_source = (
                    "visible_text"
                )

                accessible_name = (
                    text
                )

            # -------------------------------------------------
            # 2. aria-label
            # -------------------------------------------------

            elif aria_label:

                has_accessible_name = (
                    True
                )

                name_source = (
                    "aria_label"
                )

                accessible_name = (
                    aria_label
                )

                result[
                    "links_with_aria_label"
                ] += 1

            # -------------------------------------------------
            # 3. title
            # -------------------------------------------------

            elif title:

                has_accessible_name = (
                    True
                )

                name_source = (
                    "title"
                )

                accessible_name = (
                    title
                )

            # -------------------------------------------------
            # 4. Image alt
            # -------------------------------------------------

            else:

                images_inside = (
                    link.find_all(
                        "img"
                    )
                )

                for image in (
                    images_inside
                ):

                    image_alt = (
                        image.get(
                            "alt"
                        )
                    )

                    if (
                        image_alt
                        and image_alt.strip()
                    ):

                        has_accessible_name = (
                            True
                        )

                        name_source = (
                            "image_alt"
                        )

                        accessible_name = (
                            image_alt.strip()
                        )

                        break

            # -------------------------------------------------
            # Empty / inaccessible link
            # -------------------------------------------------

            if not has_accessible_name:

                result[
                    "empty_link_text"
                ] += 1

                result[
                    "link_issues"
                ].append(
                    {
                        "element":
                            "a",

                        "index":
                            index,

                        "text":
                            text,

                        "href":
                            href,

                        "aria_label":
                            aria_label,

                        "title":
                            title,

                        "accessible_name":
                            "",

                        "name_source":
                            "none",

                        "selector":
                            metadata[
                                "selector"
                            ],

                        "html_snippet":
                            metadata[
                                "html_snippet"
                            ],

                        "element_id":
                            metadata[
                                "element_id"
                            ],

                        "element_classes":
                            metadata[
                                "element_classes"
                            ],

                        "issue":
                            "empty_link_text",

                        "severity":
                            "high",

                        "reason":
                            (
                                "Link has no accessible "
                                "name. Add meaningful "
                                "link text, aria-label, "
                                "or image alt text."
                            )
                    }
                )

            # -------------------------------------------------
            # Generic link text
            # -------------------------------------------------

            elif (
                text_lower
                in generic_text
            ):

                result[
                    "generic_link_text"
                ] += 1

                result[
                    "link_issues"
                ].append(
                    {
                        "element":
                            "a",

                        "index":
                            index,

                        "text":
                            text,

                        "href":
                            href,

                        "aria_label":
                            aria_label,

                        "title":
                            title,

                        "accessible_name":
                            accessible_name,

                        "name_source":
                            name_source,

                        "selector":
                            metadata[
                                "selector"
                            ],

                        "html_snippet":
                            metadata[
                                "html_snippet"
                            ],

                        "element_id":
                            metadata[
                                "element_id"
                            ],

                        "element_classes":
                            metadata[
                                "element_classes"
                            ],

                        "issue":
                            "generic_link_text",

                        "severity":
                            "medium",

                        "reason":
                            (
                                "Link text is generic "
                                "and does not clearly "
                                "identify the destination."
                            )
                    }
                )

        # =====================================================
        # 4. PAGE TITLE
        # =====================================================

        page_title = soup.find(
            "title"
        )

        if (
            page_title
            and page_title.get_text(
                strip=True
            )
        ):

            result[
                "has_title"
            ] = 1

        # =====================================================
        # 5. LANGUAGE ATTRIBUTE
        # =====================================================

        html_tag = soup.find(
            "html"
        )

        if (
            html_tag
            and html_tag.get(
                "lang"
            )
        ):

            result[
                "has_lang"
            ] = 1

    except Exception as e:

        result[
            "error"
        ] = str(e)

    return result


# =============================================================
# TEST
# =============================================================

if __name__ == "__main__":

    url = (
        "https://www.du.ac.bd/"
    )

    result = scan_page(
        url
    )

    print()

    print(
        "Accessibility Scan"
    )

    print(
        "=" * 60
    )

    for key, value in (
        result.items()
    ):

        if key in [
            "image_issues",
            "heading_issues",
            "link_issues",
            "form_issues"
        ]:

            print(
                f"{key}: "
                f"{len(value)}"
            )

        else:

            print(
                f"{key}: "
                f"{value}"
            )

    # ---------------------------------------------------------
    # Sample evidence
    # ---------------------------------------------------------

    print()

    print(
        "=" * 60
    )

    print(
        "SAMPLE ISSUE EVIDENCE"
    )

    print(
        "=" * 60
    )

    for issue_group in [
        "image_issues",
        "heading_issues",
        "link_issues"
    ]:

        issues = result[
            issue_group
        ]

        if issues:

            print()

            print(
                issue_group.upper()
            )

            print(
                issues[0]
            )
