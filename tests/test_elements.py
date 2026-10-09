"""extract.elements: the request shape and the ``elements`` result."""

from __future__ import annotations

from types import MappingProxyType

import httpx

from conftest import json_response, make_async, make_sync, request_json
from crawlbrulee import ScrapeElementSpec, ScrapeExtract, ScrapeResponse
from crawlbrulee._serde import from_dict

BOOKS_REQUEST = {
    "heading": "h1",
    "books": {
        "selector": "article.product_pod",
        "all": True,
        "fields": {
            "title": {"selector": "h3 a", "output": "attribute", "attribute": "title"},
            "price": ".price_color",
            "url": {"selector": "h3 a", "output": "attribute", "attribute": "href"},
        },
    },
    "next_page": {"selector": "li.next a", "output": "attribute", "attribute": "href"},
}

BOOKS_ELEMENTS = {
    "heading": "All products",
    "books": [
        {
            "title": "A Light in the Attic",
            "price": "£51.77",
            "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        },
        {
            "title": "Tipping the Velvet",
            "price": "£53.74",
            "url": "https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html",
        },
    ],
    "next_page": "https://books.toscrape.com/catalogue/page-2.html",
}

PAGE = {
    "url": "https://books.toscrape.com/",
    "requested_url": "https://books.toscrape.com/",
    "elements": BOOKS_ELEMENTS,
}


def _books_extract() -> ScrapeExtract:
    return ScrapeExtract(
        elements={
            "heading": "h1",
            "books": ScrapeElementSpec(
                selector="article.product_pod",
                all=True,
                fields={
                    "title": ScrapeElementSpec(
                        selector="h3 a", output="attribute", attribute="title"
                    ),
                    "price": ".price_color",
                    "url": ScrapeElementSpec(selector="h3 a", output="attribute", attribute="href"),
                },
            ),
            "next_page": ScrapeElementSpec(
                selector="li.next a", output="attribute", attribute="href"
            ),
        }
    )


def _capture(seen: list[dict], payload: object):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request_json(request))
        return json_response(payload)

    return handler


# --- request ------------------------------------------------------------------


def test_dataclass_elements_are_sent_as_the_wire_shape() -> None:
    seen: list[dict] = []
    client = make_sync(_capture(seen, PAGE))
    client.scrape(url="https://books.toscrape.com/", extract=_books_extract())

    # Unset options (output, attribute, all) are left out, so the server defaults apply.
    assert seen[0]["extract"] == {"elements": BOOKS_REQUEST}


def test_plain_dict_elements_pass_through() -> None:
    seen: list[dict] = []
    client = make_sync(_capture(seen, PAGE))
    client.scrape(url="https://books.toscrape.com/", extract={"elements": BOOKS_REQUEST})

    assert seen[0]["extract"] == {"elements": BOOKS_REQUEST}


# The next tests also run under pyright (tests are type-checked), so they prove the
# element types accept these shapes, not only that the wire body is right.


def test_a_prebuilt_spec_map_is_accepted_as_elements_and_fields() -> None:
    seen: list[dict] = []
    client = make_sync(_capture(seen, PAGE))
    # A dict of specs only (no strings) is a dict[str, ScrapeElementSpec].
    specs = {"title": ScrapeElementSpec(selector="h1")}
    client.scrape(url="https://example.com", extract=ScrapeExtract(elements=specs))
    client.scrape(
        url="https://example.com",
        extract=ScrapeExtract(
            elements={"cards": ScrapeElementSpec(selector=".card", all=True, fields=specs)}
        ),
    )

    assert seen[0]["extract"]["elements"] == {"title": {"selector": "h1"}}
    assert seen[1]["extract"]["elements"] == {
        "cards": {"selector": ".card", "all": True, "fields": {"title": {"selector": "h1"}}}
    }


def test_plain_dict_specs_are_accepted_in_scrape_extract() -> None:
    seen: list[dict] = []
    client = make_sync(_capture(seen, PAGE))
    client.scrape(
        url="https://example.com",
        extract=ScrapeExtract(elements={"books": {"selector": "article", "all": True}}),
    )
    # Written inline (not via BOOKS_REQUEST) so pyright checks every nested key.
    client.scrape(
        url="https://example.com",
        extract=ScrapeExtract(
            elements={
                "books": {
                    "selector": "article",
                    "all": True,
                    "fields": {
                        "title": {"selector": "h3 a", "output": "attribute", "attribute": "title"},
                        "price": ".price_color",
                    },
                }
            }
        ),
    )

    assert seen[0]["extract"]["elements"] == {"books": {"selector": "article", "all": True}}
    assert seen[1]["extract"]["elements"] == {
        "books": {
            "selector": "article",
            "all": True,
            "fields": {
                "title": {"selector": "h3 a", "output": "attribute", "attribute": "title"},
                "price": ".price_color",
            },
        }
    }


def test_a_mapping_that_is_not_a_dict_is_sent_as_an_object() -> None:
    seen: list[dict] = []
    client = make_sync(_capture(seen, PAGE))
    fields = MappingProxyType({"price": ".price_color"})
    elements = MappingProxyType(
        {"books": ScrapeElementSpec(selector="article", all=True, fields=fields)}
    )
    client.scrape(url="https://example.com", extract=ScrapeExtract(elements=elements))

    assert seen[0]["extract"]["elements"] == {
        "books": {"selector": "article", "all": True, "fields": {"price": ".price_color"}}
    }


def test_fields_nest_three_levels_deep() -> None:
    seen: list[dict] = []
    client = make_sync(_capture(seen, PAGE))
    client.scrape(
        url="https://example.com",
        extract=ScrapeExtract(
            elements={
                "sections": ScrapeElementSpec(
                    selector="section",
                    all=True,
                    fields={
                        "cards": ScrapeElementSpec(
                            selector=".card",
                            all=True,
                            fields={
                                "tags": ScrapeElementSpec(selector=".tag", all=True),
                                "body": ScrapeElementSpec(selector=".body", output="html"),
                            },
                        )
                    },
                )
            }
        ),
    )

    assert seen[0]["extract"]["elements"] == {
        "sections": {
            "selector": "section",
            "all": True,
            "fields": {
                "cards": {
                    "selector": ".card",
                    "all": True,
                    "fields": {
                        "tags": {"selector": ".tag", "all": True},
                        "body": {"selector": ".body", "output": "html"},
                    },
                }
            },
        }
    }


def test_all_false_is_sent_as_given() -> None:
    seen: list[dict] = []
    client = make_sync(_capture(seen, PAGE))
    client.scrape(
        url="https://example.com",
        extract=ScrapeExtract(elements={"title": ScrapeElementSpec(selector="h1", all=False)}),
    )

    assert seen[0]["extract"]["elements"] == {"title": {"selector": "h1", "all": False}}


def test_async_job_sends_elements() -> None:
    seen: list[dict] = []
    client = make_sync(_capture(seen, {"job_id": "j1"}))
    client.scrape_async(url="https://books.toscrape.com/", extract=_books_extract())

    assert seen[0]["extract"] == {"elements": BOOKS_REQUEST}


async def test_async_client_sends_elements() -> None:
    seen: list[dict] = []
    # One stub reply that serves as both a page and a job receipt.
    async with make_async(_capture(seen, {**PAGE, "job_id": "j1"})) as client:
        await client.scrape(url="https://books.toscrape.com/", extract=_books_extract())
        await client.scrape_async(url="https://books.toscrape.com/", extract=_books_extract())

    assert len(seen) == 2
    for body in seen:
        assert body["extract"] == {"elements": BOOKS_REQUEST}


# --- response -----------------------------------------------------------------


def test_scrape_returns_elements_by_name() -> None:
    client = make_sync(_capture([], PAGE))
    page = client.scrape(url="https://books.toscrape.com/", extract=_books_extract())

    assert page.elements == BOOKS_ELEMENTS
    assert page.elements is not None
    assert page.elements["heading"] == "All products"
    books = page.elements["books"]
    assert isinstance(books, list)
    first = books[0]
    assert isinstance(first, dict)
    assert first["price"] == "£51.77"


def test_elements_keep_nulls_empty_lists_and_nested_objects() -> None:
    elements = {
        "missing": None,
        "no_matches": [],
        "tags": ["a", "b"],
        "product": {"name": "Lamp", "sku": None, "badges": [], "specs": {"color": "red"}},
        "sections": [
            {
                "title": "One",
                "cards": [{"label": "x", "tags": ["t1"], "note": None}],
            }
        ],
    }
    page = from_dict(
        ScrapeResponse,
        {
            "url": "https://example.com",
            "requested_url": "https://example.com",
            "elements": elements,
        },
    )

    assert page.elements == elements
    assert page.elements is not None
    assert page.elements["missing"] is None
    assert page.elements["no_matches"] == []


def test_elements_is_none_when_not_requested() -> None:
    page = from_dict(
        ScrapeResponse, {"url": "https://example.com", "requested_url": "https://example.com"}
    )

    assert page.elements is None


def test_json_page_reports_elements_as_unsupported() -> None:
    page = from_dict(
        ScrapeResponse,
        {
            "url": "https://example.com/data.json",
            "requested_url": "https://example.com/data.json",
            "content_type": "application/json",
            "unsupported_fields": ["elements"],
        },
    )

    assert page.unsupported_fields == ["elements"]
    assert page.elements is None


def test_elements_truncated_warning_comes_through() -> None:
    page = from_dict(
        ScrapeResponse,
        {
            "url": "https://example.com",
            "requested_url": "https://example.com",
            "elements": {"items": ["a"] * 3},
            "warnings": ["elements_truncated"],
        },
    )

    assert page.warnings == ["elements_truncated"]


def test_wait_for_scrape_returns_elements() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/api/scrape/status/"):
            return json_response({"job_id": "j1", "status": "done", "created_at": "t"})
        assert request.url.path == "/api/scrape/result/j1"
        return json_response(PAGE)

    page = make_sync(handler).wait_for_scrape("j1", interval=0.001)

    assert page.elements == BOOKS_ELEMENTS


async def test_async_client_result_returns_elements() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/api/scrape/status/"):
            return json_response({"job_id": "j1", "status": "done", "created_at": "t"})
        return json_response(PAGE)

    async with make_async(handler) as client:
        result = await client.get_scrape_result("j1")
        waited = await client.wait_for_scrape("j1", interval=0.001)

    assert result.elements == BOOKS_ELEMENTS
    assert waited.elements == BOOKS_ELEMENTS
