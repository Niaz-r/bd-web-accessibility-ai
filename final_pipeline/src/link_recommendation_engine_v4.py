import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import pandas as pd
from bs4 import BeautifulSoup


# ============================================================
# LINK RECOMMENDATION ENGINE V4
#
# Deterministic context-aware remediation for:
#   - empty_link_text
#   - generic_link_text
#   - axe link-name
#
# The engine does NOT use an LLM/VLM. It derives candidate link
# names from explicit DOM/context evidence and marks ambiguity
# for human review rather than inventing a destination.
# ============================================================

SRC_DIR = Path(__file__).resolve().parent
FINAL_PIPELINE_DIR = SRC_DIR.parent

OUTPUT_DIR = (
    FINAL_PIPELINE_DIR
    / "data"
    / "final"
    / "link_recommendations"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ELIGIBLE_CUSTOM_ISSUES = {
    "empty_link_text",
    "generic_link_text",
}

ELIGIBLE_AXE_RULES = {
    "link-name",
}

GENERIC_ENGLISH = {
    "read more",
    "more",
    "learn more",
    "click here",
    "here",
    "details",
    "view",
    "view more",
    "continue",
    "continue reading",
    "see more",
}

GENERIC_BENGALI = {
    "বিস্তারিত",
    "আরও",
    "আরো",
    "আরও পড়ুন",
    "আরও পড়ুন",
    "আরো পড়ুন",
    "আরো পড়ুন",
    "এখানে ক্লিক করুন",
    "ক্লিক করুন",
    "দেখুন",
}

SOCIAL_HOSTS = {
    "facebook.com": "Facebook",
    "www.facebook.com": "Facebook",
    "youtube.com": "YouTube",
    "www.youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "linkedin.com": "LinkedIn",
    "www.linkedin.com": "LinkedIn",
    "instagram.com": "Instagram",
    "www.instagram.com": "Instagram",
    "twitter.com": "X (Twitter)",
    "www.twitter.com": "X (Twitter)",
    "x.com": "X",
    "www.x.com": "X",
}

HIGH_VALUE_PATH_LABELS = {
    "home": "Home",
    "about": "About",
    "contact": "Contact",
    "contact-us": "Contact us",
    "admission": "Admission",
    "admissions": "Admissions",
    "apply": "Apply",
    "login": "Log in",
    "signin": "Sign in",
    "sign-in": "Sign in",
    "register": "Register",
    "search": "Search",
    "news": "News",
    "events": "Events",
    "event": "Event",
    "notice": "Notices",
    "notices": "Notices",
    "notice-board": "Notice board",
    "research": "Research",
    "library": "Library",
    "libraries": "Libraries",
    "faculty": "Faculty",
    "faculties": "Faculties",
    "department": "Department",
    "departments": "Departments",
    "academics": "Academics",
    "academic": "Academic information",
    "calendar": "Calendar",
    "career": "Career",
    "careers": "Careers",
    "jobs": "Jobs",
    "faq": "FAQ",
    "privacy": "Privacy policy",
    "privacy-policy": "Privacy policy",
    "terms": "Terms",
}

TEXT_FIELDS = [
    "text",
    "link_text",
    "custom_text",
    "visible_text",
]

ACCESSIBLE_NAME_FIELDS = [
    "accessible_name",
    "aria_label",
    "custom_accessible_name",
    "custom_aria_label",
]

HREF_FIELDS = [
    "href",
    "custom_href",
    "preferred_href",
]

HTML_FIELDS = [
    "preferred_html",
    "custom_html",
    "html_snippet",
    "html",
]

HEADING_FIELDS = [
    "nearby_heading",
    "nearest_heading",
    "context_heading",
    "card_heading",
    "parent_heading",
    "section_heading",
    "reliable_heading",
]

CONTEXT_FIELDS = [
    "surrounding_context",
    "context",
    "context_text",
    "reliable_context",
    "nearby_text",
    "parent_text",
    "sibling_text",
]

PAGE_TITLE_FIELDS = [
    "page_title",
    "context_page_title",
    "document_title",
]


# ============================================================
# BASIC HELPERS
# ============================================================

def clean(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return re.sub(r"\s+", " ", str(value)).strip()


def bool_value(value):
    if isinstance(value, bool):
        return value

    return clean(value).lower() in {
        "true",
        "1",
        "yes",
    }


def first_value(row, names):
    for name in names:
        value = clean(row.get(name, ""))
        if value:
            return value, name

    return "", ""


def normalize_text(value):
    return clean(value).lower()


def strip_generic_prefix(text):
    text = clean(text)
    text = re.sub(
        r"^(read\s+more|learn\s+more|view\s+more|see\s+more|details?)\s*[:\-–—]?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^(আরও\s*[পপ][ড়ড়]ুন|আরো\s*[পপ][ড়ড়]ুন|বিস্তারিত)\s*[:\-–—]?\s*",
        "",
        text,
    )

    return clean(text)


def truncate(text, max_length=110):
    text = clean(text)
    if len(text) <= max_length:
        return text

    shortened = text[:max_length].rsplit(" ", 1)[0].strip()
    return (shortened or text[:max_length]).rstrip(".,;:-") + "…"


def is_generic_link_text(text):
    text_normalized = normalize_text(text)

    if not text_normalized:
        return False

    if text_normalized in GENERIC_ENGLISH:
        return True

    if clean(text) in GENERIC_BENGALI:
        return True

    return False


def is_bengali(text):
    return bool(re.search(r"[\u0980-\u09FF]", clean(text)))


def slug_to_label(slug):
    slug = clean(unquote(slug)).strip("/ ")

    if not slug:
        return ""

    slug_lower = slug.lower()

    if slug_lower in HIGH_VALUE_PATH_LABELS:
        return HIGH_VALUE_PATH_LABELS[slug_lower]

    slug = re.sub(r"[-_]+", " ", slug)
    slug = re.sub(r"\s+", " ", slug).strip()

    # Reject opaque numeric/token-like slugs.
    if not slug:
        return ""

    if re.fullmatch(r"[0-9\W_]+", slug):
        return ""

    if len(slug) > 70:
        return ""

    words = slug.split()

    if len(words) > 8:
        return ""

    if is_bengali(slug):
        return slug

    return slug[0].upper() + slug[1:] if slug else ""


def page_identity(page_title, page_url):
    title = clean(page_title)

    if title:
        pieces = re.split(r"\s*(?:\||::|—|–)\s*", title)
        pieces = [clean(piece) for piece in pieces if clean(piece)]

        # Prefer a concise institution/site component, not generic "Home".
        non_generic = [
            piece
            for piece in pieces
            if normalize_text(piece)
            not in {
                "home",
                "homepage",
                "news",
                "contact",
                "about",
            }
        ]

        candidates = non_generic or pieces

        if candidates:
            # For titles such as "Home :: Dhaka University", last piece is useful.
            candidate = candidates[-1]
            if 2 <= len(candidate) <= 70:
                return candidate

    return ""


# ============================================================
# HTML HELPERS
# ============================================================

def parse_link_html(html_text):
    html_text = clean(html_text)

    if not html_text:
        return None

    try:
        soup = BeautifulSoup(html_text, "html.parser")
        return soup.find("a")
    except Exception:
        return None


def html_icon_tokens(html_text):
    html_text = clean(html_text).lower()

    tokens = []

    patterns = {
        "search": [
            "fa-search",
            "ti-search",
            "icon-search",
            "search-icon",
            "bi-search",
        ],
        "facebook": [
            "fa-facebook",
            "facebook-f",
            "icon-facebook",
        ],
        "youtube": [
            "fa-youtube",
            "icon-youtube",
        ],
        "linkedin": [
            "fa-linkedin",
            "icon-linkedin",
        ],
        "instagram": [
            "fa-instagram",
            "icon-instagram",
        ],
        "twitter": [
            "fa-twitter",
            "fa-x-twitter",
            "icon-twitter",
        ],
        "menu": [
            "fa-bars",
            "navbar-toggler",
            "menu-icon",
            "hamburger",
        ],
    }

    for label, values in patterns.items():
        if any(value in html_text for value in values):
            tokens.append(label)

    return tokens


def build_suggested_html(original_html, suggested_name, mode):
    original_html = clean(original_html)
    suggested_name = clean(suggested_name)

    if not original_html or not suggested_name:
        return ""

    try:
        soup = BeautifulSoup(original_html, "html.parser")
        link = soup.find("a")

        if link is None:
            return ""

        if mode == "replace_visible_text":
            # Only replace safely when the link does not contain meaningful
            # non-text descendants that should be preserved.
            significant_children = [
                child
                for child in link.children
                if getattr(child, "name", None)
                in {
                    "img",
                    "svg",
                    "i",
                    "span",
                }
            ]

            if not significant_children:
                link.clear()
                link.string = suggested_name
            else:
                # Preserve design/content and expose a specific name.
                link["aria-label"] = suggested_name

        else:
            link["aria-label"] = suggested_name

        return str(link)

    except Exception:
        return ""


# ============================================================
# DESTINATION / PURPOSE EVIDENCE
# ============================================================

def destination_evidence(href, html_text, page_title, page_url):
    href = clean(href)
    html_text = clean(html_text)

    if not href:
        return None

    # --------------------------------------------------------
    # Email / telephone
    # --------------------------------------------------------

    if href.lower().startswith("mailto:"):
        address = href.split(":", 1)[1].split("?", 1)[0].strip()
        return {
            "name": f"Email {address}" if address else "Send email",
            "evidence": "mailto destination",
            "confidence": "high",
            "decision": "mailto_destination",
        }

    if href.lower().startswith("tel:"):
        number = href.split(":", 1)[1].strip()
        return {
            "name": f"Call {number}" if number else "Call",
            "evidence": "telephone destination",
            "confidence": "high",
            "decision": "telephone_destination",
        }

    # --------------------------------------------------------
    # Hash / JS-like links: require explicit icon/function evidence.
    # --------------------------------------------------------

    if href in {"#", "javascript:void(0)", "javascript:void(0);"}:
        icons = html_icon_tokens(html_text)

        if "search" in icons:
            return {
                "name": "Search",
                "evidence": "explicit search icon in link HTML",
                "confidence": "high",
                "decision": "icon_function_search",
            }

        if "menu" in icons:
            return {
                "name": "Menu",
                "evidence": "explicit menu icon in link HTML",
                "confidence": "medium",
                "decision": "icon_function_menu",
            }

        return None

    try:
        parsed = urlparse(href)
    except Exception:
        return None

    host = (parsed.hostname or "").lower()

    # --------------------------------------------------------
    # Social destination
    # --------------------------------------------------------

    service = SOCIAL_HOSTS.get(host)

    if service:
        identity = page_identity(page_title, page_url)

        if identity and identity not in host:
            suggested = f"{identity} on {service}"
        else:
            suggested = f"{service} page"

        return {
            "name": suggested,
            "evidence": f"explicit {service} destination URL",
            "confidence": "high",
            "decision": "social_destination",
        }

    # --------------------------------------------------------
    # Explicit path semantics
    # --------------------------------------------------------

    path_parts = [
        part
        for part in (parsed.path or "").split("/")
        if clean(part)
    ]

    if path_parts:
        last = path_parts[-1]
        label = slug_to_label(last)

        if label:
            known = last.lower() in HIGH_VALUE_PATH_LABELS

            return {
                "name": label,
                "evidence": "link destination path",
                "confidence": "high" if known else "medium",
                "decision": (
                    "known_destination_path"
                    if known
                    else "destination_slug"
                ),
            }

    return None


# ============================================================
# CONTEXT EVIDENCE
# ============================================================

def context_evidence(row, visible_text):
    # --------------------------------------------------------
    # Prefer an existing V3 contextual suggestion if it is a
    # concrete, non-placeholder phrase.
    # --------------------------------------------------------

    v3_suggestion = clean(
        row.get("contextual_suggestion", "")
    )

    if (
        bool_value(row.get("contextual_processed", False))
        and v3_suggestion
    ):
        candidate = strip_generic_prefix(v3_suggestion)

        placeholders = {
            "describe the link destination",
            "use descriptive link text",
            "manual review required",
        }

        if normalize_text(candidate) not in placeholders and len(candidate) >= 3:
            return {
                "context": candidate,
                "source": "V3 contextual suggestion",
                "confidence": clean(
                    row.get("contextual_confidence", "")
                ).lower() or "medium",
            }

    heading, heading_source = first_value(row, HEADING_FIELDS)

    if heading:
        return {
            "context": truncate(heading),
            "source": heading_source,
            "confidence": "high",
        }

    context, context_source = first_value(row, CONTEXT_FIELDS)

    if context:
        # Avoid using a massive block as a link label. Prefer short context.
        context = truncate(context)

        if len(context) <= 110:
            return {
                "context": context,
                "source": context_source,
                "confidence": "medium",
            }

    return None


# ============================================================
# NAME GENERATION
# ============================================================

def generic_text_with_context(visible_text, context_text):
    visible = normalize_text(visible_text)
    context_text = clean(context_text)

    if not context_text:
        return ""

    if is_bengali(visible_text) or is_bengali(context_text):
        if visible in {
            "আরও পড়ুন",
            "আরও পড়ুন",
            "আরো পড়ুন",
            "আরো পড়ুন",
        }:
            return truncate(f"আরও পড়ুন: {context_text}")

        return truncate(f"বিস্তারিত: {context_text}")

    if visible in {
        "learn more",
    }:
        return truncate(f"Learn more about {context_text}")

    if visible in {
        "view",
        "view more",
        "see more",
    }:
        return truncate(f"View {context_text}")

    if visible in {
        "details",
    }:
        return truncate(f"Details about {context_text}")

    return truncate(f"Read more about {context_text}")


def determine_link_recommendation(row):
    custom_issue = normalize_text(
        row.get("custom_issue", "")
    )

    axe_rule = normalize_text(
        row.get("axe_rule", "")
    )

    if (
        custom_issue not in ELIGIBLE_CUSTOM_ISSUES
        and axe_rule not in ELIGIBLE_AXE_RULES
    ):
        return None

    visible_text, visible_source = first_value(
        row,
        TEXT_FIELDS,
    )

    accessible_name, accessible_source = first_value(
        row,
        ACCESSIBLE_NAME_FIELDS,
    )

    href, href_source = first_value(
        row,
        HREF_FIELDS,
    )

    html_text, html_source = first_value(
        row,
        HTML_FIELDS,
    )

    page_title, _ = first_value(
        row,
        PAGE_TITLE_FIELDS,
    )

    page_url = clean(
        row.get("page_url", "")
    )

    generic_issue = (
        custom_issue == "generic_link_text"
        or is_generic_link_text(visible_text)
    )

    missing_name_issue = (
        custom_issue == "empty_link_text"
        or axe_rule == "link-name"
    )

    destination = destination_evidence(
        href,
        html_text,
        page_title,
        page_url,
    )

    context = context_evidence(
        row,
        visible_text,
    )

    # ========================================================
    # GENERIC LINK TEXT
    # ========================================================

    if generic_issue:
        if context:
            suggested_name = generic_text_with_context(
                visible_text,
                context["context"],
            )

            confidence = (
                "high"
                if context["confidence"] == "high"
                else "medium"
            )

            suggested_html = build_suggested_html(
                html_text,
                suggested_name,
                "replace_visible_text",
            )

            return {
                "link_v4_processed": True,
                "link_v4_issue_family": "generic_link_text",
                "link_v4_decision_code": "context_specific_visible_text",
                "link_v4_current_text": visible_text,
                "link_v4_current_accessible_name": accessible_name,
                "link_v4_href": href,
                "link_v4_suggested_name": suggested_name,
                "link_v4_recommended_action": (
                    "Replace generic wording with link text that identifies "
                    "the destination or topic. Prefer meaningful visible text "
                    "when practical."
                ),
                "link_v4_confidence": confidence,
                "link_v4_evidence_source": context["source"],
                "link_v4_evidence_text": context["context"],
                "link_v4_reason": (
                    "The current wording is generic, while nearby/programmatic "
                    "context provides a more specific destination or topic."
                ),
                "link_v4_suggested_html": suggested_html,
                "link_v4_manual_review_required": True,
                "link_v4_semantics_review_required": False,
            }

        if destination and destination["confidence"] in {"high", "medium"}:
            suggested_name = destination["name"]

            # For generic "Read More", a raw social/path label may be awkward,
            # but it is still preferable to inventing context. Keep medium at most.
            suggested_html = build_suggested_html(
                html_text,
                suggested_name,
                "replace_visible_text",
            )

            return {
                "link_v4_processed": True,
                "link_v4_issue_family": "generic_link_text",
                "link_v4_decision_code": destination["decision"],
                "link_v4_current_text": visible_text,
                "link_v4_current_accessible_name": accessible_name,
                "link_v4_href": href,
                "link_v4_suggested_name": suggested_name,
                "link_v4_recommended_action": (
                    "Replace the generic link wording with text that describes "
                    "the known destination. Verify the final wording in context."
                ),
                "link_v4_confidence": "medium",
                "link_v4_evidence_source": destination["evidence"],
                "link_v4_evidence_text": href,
                "link_v4_reason": (
                    "The destination URL provides useful semantic evidence, "
                    "but nearby contextual wording was not available."
                ),
                "link_v4_suggested_html": suggested_html,
                "link_v4_manual_review_required": True,
                "link_v4_semantics_review_required": False,
            }

        return {
            "link_v4_processed": True,
            "link_v4_issue_family": "generic_link_text",
            "link_v4_decision_code": "insufficient_context",
            "link_v4_current_text": visible_text,
            "link_v4_current_accessible_name": accessible_name,
            "link_v4_href": href,
            "link_v4_suggested_name": "",
            "link_v4_recommended_action": (
                "Review the link's programmatic context and destination. Replace "
                "generic wording with a specific link name only when the intended "
                "purpose can be established reliably."
            ),
            "link_v4_confidence": "low",
            "link_v4_evidence_source": "insufficient evidence",
            "link_v4_evidence_text": "",
            "link_v4_reason": (
                "The available DOM and contextual evidence is not strong enough "
                "to generate a specific link name safely."
            ),
            "link_v4_suggested_html": "",
            "link_v4_manual_review_required": True,
            "link_v4_semantics_review_required": href in {"#", ""},
        }

    # ========================================================
    # EMPTY / MISSING ACCESSIBLE NAME
    # ========================================================

    if missing_name_issue:
        # If the custom extraction already sees a meaningful accessible name
        # while axe reports link-name, preserve the rendered-DOM conflict for review.
        if accessible_name and not is_generic_link_text(accessible_name):
            return {
                "link_v4_processed": True,
                "link_v4_issue_family": "missing_accessible_name",
                "link_v4_decision_code": "name_evidence_conflict",
                "link_v4_current_text": visible_text,
                "link_v4_current_accessible_name": accessible_name,
                "link_v4_href": href,
                "link_v4_suggested_name": accessible_name,
                "link_v4_recommended_action": (
                    "Verify the computed accessible name in the rendered browser "
                    "accessibility tree. The static evidence contains a candidate "
                    "name, but axe reported the rendered link as unnamed."
                ),
                "link_v4_confidence": "medium",
                "link_v4_evidence_source": accessible_source,
                "link_v4_evidence_text": accessible_name,
                "link_v4_reason": (
                    "Static and rendered-DOM evidence disagree about the link name."
                ),
                "link_v4_suggested_html": "",
                "link_v4_manual_review_required": True,
                "link_v4_semantics_review_required": False,
            }

        if destination:
            suggested_name = destination["name"]
            icon_tokens = html_icon_tokens(html_text)

            # Icon-only links should generally preserve the visual icon and gain
            # an accessible name rather than inserting visible text blindly.
            mode = "aria_label"

            suggested_html = build_suggested_html(
                html_text,
                suggested_name,
                mode,
            )

            semantics_review = (
                href in {"#", "javascript:void(0)", "javascript:void(0);"}
            )

            if destination["decision"] == "icon_function_search":
                action = (
                    "Expose the search control with the accessible name 'Search'. "
                    "If activating it performs an interface action rather than "
                    "navigation, also review whether a <button> is the more "
                    "appropriate semantic element."
                )
            else:
                action = (
                    "Provide the link with an accessible name describing its "
                    "destination or function. Preserve meaningful visible content "
                    "and avoid redundant wording."
                )

            return {
                "link_v4_processed": True,
                "link_v4_issue_family": "missing_accessible_name",
                "link_v4_decision_code": destination["decision"],
                "link_v4_current_text": visible_text,
                "link_v4_current_accessible_name": accessible_name,
                "link_v4_href": href,
                "link_v4_suggested_name": suggested_name,
                "link_v4_recommended_action": action,
                "link_v4_confidence": destination["confidence"],
                "link_v4_evidence_source": destination["evidence"],
                "link_v4_evidence_text": href or ", ".join(icon_tokens),
                "link_v4_reason": (
                    "The destination/function can be derived from explicit link "
                    "or icon evidence without guessing visual meaning."
                ),
                "link_v4_suggested_html": suggested_html,
                "link_v4_manual_review_required": True,
                "link_v4_semantics_review_required": semantics_review,
            }

        if context:
            suggested_name = clean(context["context"])
            suggested_html = build_suggested_html(
                html_text,
                suggested_name,
                "aria_label",
            )

            return {
                "link_v4_processed": True,
                "link_v4_issue_family": "missing_accessible_name",
                "link_v4_decision_code": "context_derived_name",
                "link_v4_current_text": visible_text,
                "link_v4_current_accessible_name": accessible_name,
                "link_v4_href": href,
                "link_v4_suggested_name": suggested_name,
                "link_v4_recommended_action": (
                    "Provide an accessible link name reflecting the established "
                    "nearby/programmatic context. Verify that this context really "
                    "describes the link destination or action."
                ),
                "link_v4_confidence": context["confidence"],
                "link_v4_evidence_source": context["source"],
                "link_v4_evidence_text": context["context"],
                "link_v4_reason": (
                    "Nearby/programmatic context supplies a candidate purpose for "
                    "the otherwise unnamed link."
                ),
                "link_v4_suggested_html": suggested_html,
                "link_v4_manual_review_required": True,
                "link_v4_semantics_review_required": href in {"#", ""},
            }

        return {
            "link_v4_processed": True,
            "link_v4_issue_family": "missing_accessible_name",
            "link_v4_decision_code": "insufficient_evidence",
            "link_v4_current_text": visible_text,
            "link_v4_current_accessible_name": accessible_name,
            "link_v4_href": href,
            "link_v4_suggested_name": "",
            "link_v4_recommended_action": (
                "Inspect the link's actual destination or action and provide a "
                "concise accessible name describing that purpose. Do not invent a "
                "name from weak visual or filename evidence."
            ),
            "link_v4_confidence": "low",
            "link_v4_evidence_source": "insufficient evidence",
            "link_v4_evidence_text": "",
            "link_v4_reason": (
                "No reliable destination, functional icon, accessible-name source, "
                "or specific contextual evidence was available."
            ),
            "link_v4_suggested_html": "",
            "link_v4_manual_review_required": True,
            "link_v4_semantics_review_required": href in {"#", ""},
        }

    return None


# ============================================================
# OUTPUT BASENAME
# ============================================================

def derive_base_name(input_file):
    name = os.path.basename(input_file)

    suffixes = [
        "__contextual_recommendations.csv",
        "_contextual_recommendations.csv",
        "__context_findings.csv",
        "_context_findings.csv",
        "__unified_findings.csv",
        "_unified_findings.csv",
    ]

    for suffix in suffixes:
        if name.endswith(suffix):
            return name[:-len(suffix)]

    return os.path.splitext(name)[0]


# ============================================================
# MAIN PROCESSOR
# ============================================================

def process_file(input_file):
    input_file = Path(input_file)

    if not input_file.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_file}"
        )

    df = pd.read_csv(input_file)

    print()
    print("=" * 80)
    print("LINK RECOMMENDATION ENGINE V4")
    print("=" * 80)
    print("Input:", input_file)
    print("Total findings:", len(df))

    boolean_columns = [
        "link_v4_processed",
        "link_v4_manual_review_required",
        "link_v4_semantics_review_required",
    ]

    text_columns = [
        "link_v4_issue_family",
        "link_v4_decision_code",
        "link_v4_current_text",
        "link_v4_current_accessible_name",
        "link_v4_href",
        "link_v4_suggested_name",
        "link_v4_recommended_action",
        "link_v4_confidence",
        "link_v4_evidence_source",
        "link_v4_evidence_text",
        "link_v4_reason",
        "link_v4_suggested_html",
    ]

    for column in boolean_columns:
        df[column] = pd.Series(
            [False] * len(df),
            index=df.index,
            dtype="boolean",
        )

    for column in text_columns:
        df[column] = pd.Series(
            [""] * len(df),
            index=df.index,
            dtype="object",
        )

    processed_count = 0

    for index, row in df.iterrows():
        result = determine_link_recommendation(row)

        if result is None:
            continue

        processed_count += 1

        for key, value in result.items():
            df.at[index, key] = value

    base_name = derive_base_name(str(input_file))

    output_file = (
        OUTPUT_DIR
        / f"{base_name}__link_recommendations.csv"
    )

    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig",
    )

    processed_df = df[
        df["link_v4_processed"].fillna(False)
    ]

    print()
    print("=" * 80)
    print("LINK V4 SUMMARY")
    print("=" * 80)
    print("Processed link findings:", processed_count)

    if len(processed_df):
        print()
        print("Issue families:")
        print(
            processed_df[
                "link_v4_issue_family"
            ].value_counts().to_string()
        )

        print()
        print("Decision codes:")
        print(
            processed_df[
                "link_v4_decision_code"
            ].value_counts().to_string()
        )

        print()
        print("Confidence:")
        print(
            processed_df[
                "link_v4_confidence"
            ].value_counts().to_string()
        )

        suggestions = int(
            processed_df[
                "link_v4_suggested_name"
            ].astype(str).str.strip().ne("").sum()
        )

        manual_only = int(
            processed_df[
                "link_v4_suggested_name"
            ].astype(str).str.strip().eq("").sum()
        )

        print()
        print("Specific candidate names:", suggestions)
        print("Manual-review only:", manual_only)

    print()
    print("Output:")
    print(output_file)
    print()
    print(
        "Important: candidate link names are deterministic "
        "decision-support suggestions and require human verification."
    )

    return output_file


def main():
    if len(sys.argv) < 2:
        print()
        print("Usage:")
        print(
            "python final_pipeline/src/"
            "link_recommendation_engine_v4.py "
            "<contextual_or_context_findings.csv>"
        )
        print()
        sys.exit(1)

    process_file(sys.argv[1])


if __name__ == "__main__":
    main()
