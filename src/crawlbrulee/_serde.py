"""(De)serialization between dataclass DTOs and the wire JSON.

``to_dict`` builds request bodies (omitting ``None`` so server defaults apply);
``from_dict`` builds response dataclasses from parsed JSON. Both honor an
optional ``__wire_aliases__`` class attribute mapping field names to wire keys.
"""

from __future__ import annotations

import dataclasses
import types as _types
from functools import cache
from typing import Any, TypeVar, Union, get_args, get_origin, get_type_hints

T = TypeVar("T")


@cache
def _type_hints(cls: type) -> dict[str, Any]:
    """Resolved type hints for ``cls``, cached -- ``get_type_hints`` is costly
    and a response class's hints never change for the life of the process."""
    return get_type_hints(cls)


def to_dict(obj: Any) -> Any:
    """Recursively convert a dataclass / list / dict to a JSON-ready value,
    omitting ``None`` fields. Plain values pass through unchanged."""
    if obj is None:
        return None
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        aliases: dict[str, str] = getattr(type(obj), "__wire_aliases__", {})
        out: dict[str, Any] = {}
        for f in dataclasses.fields(obj):
            value = getattr(obj, f.name)
            if value is None:
                continue
            out[aliases.get(f.name, f.name)] = to_dict(value)
        return out
    if isinstance(obj, (list, tuple)):
        return [to_dict(v) for v in obj]
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items() if v is not None}
    return obj


def from_dict(cls: type[T], data: Any) -> T:
    """Construct a dataclass of type ``cls`` from a parsed-JSON ``dict``.

    Handles ``Optional``, ``list[X]``, and nested dataclasses. Unknown keys in
    ``data`` are ignored, so new server fields don't break older SDK versions.
    """
    hints = _type_hints(cls)
    aliases: dict[str, str] = getattr(cls, "__wire_aliases__", {})
    kwargs: dict[str, Any] = {}
    for f in dataclasses.fields(cls):  # type: ignore[arg-type]
        wire_key = aliases.get(f.name, f.name)
        if wire_key not in data:
            continue
        kwargs[f.name] = _convert(hints.get(f.name, Any), data[wire_key])
    return cls(**kwargs)


def _convert(hint: Any, value: Any) -> Any:
    # A wire null maps to None regardless of the declared type. This also guards
    # the list/nested-dataclass branches below against a server sending null for
    # a field the schema types as required (non-Optional).
    if value is None:
        return None

    origin = get_origin(hint)

    # Optional[X] / Union[...] / X | Y
    if origin is Union or origin is _types.UnionType:
        non_none = [a for a in get_args(hint) if a is not type(None)]
        if len(non_none) == 1:
            return _convert(non_none[0], value)
        # Ambiguous union (e.g. int | str) -- pass the raw value through.
        return value

    # list[X] / tuple[X, ...]
    if origin in (list, tuple):
        args = get_args(hint)
        item_hint = args[0] if args else Any
        return [_convert(item_hint, v) for v in value]

    # Nested dataclass
    if dataclasses.is_dataclass(hint) and isinstance(hint, type):
        return from_dict(hint, value)

    # Primitive, Literal, Any, etc.
    return value


def _build_body(fields: dict[str, Any]) -> dict[str, Any]:
    """Drop ``None``-valued fields so the server's defaults apply."""
    return {k: v for k, v in fields.items() if v is not None}


def scrape_body(
    url: str,
    extract: Any,
    cache: Any,
    require_js: bool | None,
    exclude_selectors: list[str] | None,
    proxy: str | None,
    location: Any,
) -> dict[str, Any]:
    """Build the JSON body for ``/api/scrape`` and ``/api/scrape/async``."""
    return _build_body(
        {
            "url": url,
            "extract": to_dict(extract),
            "cache": to_dict(cache),
            "require_js": require_js,
            "exclude_selectors": exclude_selectors,
            "proxy": proxy,
            "location": to_dict(location),
        }
    )


def async_scrape_body(
    url: str,
    extract: Any,
    cache: Any,
    require_js: bool | None,
    exclude_selectors: list[str] | None,
    proxy: str | None,
    location: Any,
    webhook: Any,
) -> dict[str, Any]:
    """Build the JSON body for ``/api/scrape/async``.

    Same as :func:`scrape_body` plus the async-only ``webhook`` field. The sync
    ``/api/scrape`` schema rejects ``webhook``, so it lives only here.
    """
    body = scrape_body(url, extract, cache, require_js, exclude_selectors, proxy, location)
    serialized = to_dict(webhook)
    if serialized is not None:
        body["webhook"] = serialized
    return body


def map_body(
    url: str,
    proxy: str | None,
    sitemap_only: bool | None,
    types: Any,
    cache: Any,
    max_urls: int | None,
    page: int | None,
    limit: int | None,
    location: Any,
) -> dict[str, Any]:
    """Build the JSON body for ``/api/map``."""
    return _build_body(
        {
            "url": url,
            "proxy": proxy,
            "sitemap_only": sitemap_only,
            "types": to_dict(types),
            "cache": to_dict(cache),
            "max_urls": max_urls,
            "page": page,
            "limit": limit,
            "location": to_dict(location),
        }
    )
