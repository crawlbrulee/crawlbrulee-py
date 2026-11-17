"""pdf output and dark mode: ``extract.pdf``, ``ScreenshotRequest.color_scheme``,
the top-level ``pdf`` result, the two pdf warnings and ``unsupported_pdf_output``."""

from __future__ import annotations

import contextlib
from typing import get_args

import httpx
import pytest

from conftest import json_response, make_async, make_sync, request_json
from crawlbrulee import (
    PdfLayout,
    PdfMedia,
    PdfPaper,
    PdfRequest,
    PdfResult,
    ScrapeExtract,
    ScrapeResponse,
    ScrapeWarningCode,
    ScreenshotColorScheme,
    ScreenshotRequest,
    ValidationError,
)
from crawlbrulee._serde import from_dict, scrape_body

PAGE = {"url": "https://example.com/report", "requested_url": "https://example.com/report"}
PDF = {"url": "https://cdn.example.com/pdf/abc.pdf?token=t", "bytes": 48213}


def _capture(seen: list[dict], payload: object = None):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append({"path": request.url.path, "body": request_json(request)})
        return json_response(payload if payload is not None else {"job_id": "j1"})

    return handler


# --------------------------------------------------------------------------
# request
# --------------------------------------------------------------------------


def test_empty_pdf_request_is_sent_as_an_empty_object() -> None:
    body = scrape_body(
        PAGE["url"],
        ScrapeExtract(markdown=False, metadata=False, pdf=PdfRequest()),
        None,
        None,
        None,
        None,
        None,
    )
    assert body["extract"] == {"markdown": False, "metadata": False, "pdf": {}}


def test_plain_dict_pdf_is_sent_as_an_empty_object() -> None:
    body = scrape_body(PAGE["url"], {"pdf": {}}, None, None, None, None, None)
    assert body["extract"] == {"pdf": {}}


def test_every_pdf_option_is_sent() -> None:
    pdf = PdfRequest(layout="pages", paper="letter", landscape=True, media="print")
    body = scrape_body(PAGE["url"], ScrapeExtract(pdf=pdf), None, None, None, None, None)
    assert body["extract"] == {
        "pdf": {"layout": "pages", "paper": "letter", "landscape": True, "media": "print"}
    }


def test_pdf_left_out_when_not_given() -> None:
    body = scrape_body(PAGE["url"], ScrapeExtract(markdown=True), None, None, None, None, None)
    assert "pdf" not in body["extract"]


def test_color_scheme_is_sent_next_to_a_pdf() -> None:
    extract = ScrapeExtract(
        screenshot=ScreenshotRequest(type="full_page", color_scheme="dark"),
        pdf=PdfRequest(),
    )
    body = scrape_body(PAGE["url"], extract, None, None, None, None, None)
    assert body["extract"] == {
        "screenshot": {"type": "full_page", "color_scheme": "dark"},
        "pdf": {},
    }


def test_color_scheme_left_out_when_not_given() -> None:
    extract = ScrapeExtract(screenshot=ScreenshotRequest(type="viewport"))
    body = scrape_body(PAGE["url"], extract, None, None, None, None, None)
    assert body["extract"]["screenshot"] == {"type": "viewport"}


def test_sync_client_sends_pdf_on_both_scrape_calls() -> None:
    seen: list[dict] = []
    client = make_sync(_capture(seen))
    extract = ScrapeExtract(
        screenshot=ScreenshotRequest(type="viewport", color_scheme="dark"),
        pdf=PdfRequest(layout="single_page", media="print"),
    )
    with contextlib.suppress(Exception):  # stub reply is no full result; only the body counts
        client.scrape(url=PAGE["url"], extract=extract)
    client.scrape_async(url=PAGE["url"], extract=extract)

    assert [s["path"] for s in seen] == ["/api/scrape", "/api/scrape/async"]
    for s in seen:
        assert s["body"]["extract"] == {
            "screenshot": {"type": "viewport", "color_scheme": "dark"},
            "pdf": {"layout": "single_page", "media": "print"},
        }


async def test_async_client_sends_pdf_on_both_scrape_calls() -> None:
    seen: list[dict] = []
    async with make_async(_capture(seen)) as client:
        with contextlib.suppress(Exception):
            await client.scrape(url=PAGE["url"], extract={"pdf": {}})
        await client.scrape_async(url=PAGE["url"], extract=ScrapeExtract(pdf=PdfRequest()))

    assert [s["path"] for s in seen] == ["/api/scrape", "/api/scrape/async"]
    for s in seen:
        assert s["body"]["extract"] == {"pdf": {}}


# --------------------------------------------------------------------------
# response
# --------------------------------------------------------------------------


def test_pdf_result_is_parsed() -> None:
    client = make_sync(lambda _r: json_response({**PAGE, "markdown": "# Report", "pdf": PDF}))
    page = client.scrape(url=PAGE["url"], extract=ScrapeExtract(pdf=PdfRequest()))

    assert isinstance(page.pdf, PdfResult)
    assert page.pdf.url == PDF["url"]
    assert page.pdf.bytes == 48213
    assert page.markdown == "# Report"


def test_pdf_is_none_when_not_sent() -> None:
    page = from_dict(ScrapeResponse, PAGE)
    assert page.pdf is None


def test_pdf_unavailable_leaves_pdf_out_and_keeps_the_rest() -> None:
    page = from_dict(
        ScrapeResponse, {**PAGE, "markdown": "# Report", "warnings": ["pdf_unavailable"]}
    )
    assert page.pdf is None
    assert page.warnings == ["pdf_unavailable"]
    assert page.markdown == "# Report"


def test_pdf_single_page_overflow_comes_with_the_pdf() -> None:
    page = from_dict(ScrapeResponse, {**PAGE, "pdf": PDF, "warnings": ["pdf_single_page_overflow"]})
    assert page.pdf is not None
    assert page.warnings == ["pdf_single_page_overflow"]


def test_warning_codes_include_both_pdf_codes() -> None:
    codes = get_args(ScrapeWarningCode)
    assert "pdf_unavailable" in codes
    assert "pdf_single_page_overflow" in codes


def test_unsupported_pdf_output_raises_validation_error() -> None:
    client = make_sync(
        lambda _r: json_response(
            {
                "name": "unsupported_pdf_output",
                "message": "This content type cannot be saved as a PDF.",
            },
            422,
        )
    )
    with pytest.raises(ValidationError) as info:
        client.scrape(
            url="https://example.com/data.json",
            extract=ScrapeExtract(markdown=False, metadata=False, pdf=PdfRequest()),
        )
    assert info.value.error_name == "unsupported_pdf_output"
    assert info.value.status == 422


# --------------------------------------------------------------------------
# types
# --------------------------------------------------------------------------


def test_option_values() -> None:
    assert set(get_args(PdfLayout)) == {"pages", "single_page"}
    assert set(get_args(PdfPaper)) == {"a4", "letter"}
    assert set(get_args(PdfMedia)) == {"screen", "print"}
    assert set(get_args(ScreenshotColorScheme)) == {"light", "dark"}


def test_new_fields_default_to_none() -> None:
    # Every pdf option is optional, so PdfRequest() is the "take every default" form,
    # and the new fields on older shapes don't change how they are built.
    assert PdfRequest() == PdfRequest(layout=None, paper=None, landscape=None, media=None)
    assert ScrapeExtract().pdf is None
    assert ScreenshotRequest(type="viewport").color_scheme is None
