"""MCP tools for the CMS DBS3 Python client."""

from __future__ import annotations

import inspect
import os
from functools import lru_cache
from typing import Any
from dbs.apis.dbsClient import DbsApi

from mcp.server.fastmcp import FastMCP


DEFAULT_DBS_URL = "https://cmsweb.cern.ch/dbs/prod/global/DBSReader/"
WRITE_METHOD_PREFIXES = ("insert", "submit", "remove")
BLOCKED_METHODS = {
    "requestTimingInfo",
    "requestContentLength",
}

host = os.getenv("MCP_HOST", "0.0.0.0")
port = int(os.getenv("MCP_PORT", "8013"))
mcp = FastMCP("dbs", host=host, port=port)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc


@lru_cache(maxsize=1)
def _dbs_client() -> Any:
    dbs_client = DbsApi(
        url=os.getenv("DBS_URL", DEFAULT_DBS_URL),
        proxy=os.getenv("DBS_PROXY") or None,
        key=os.getenv("X509_USER_PROXY") or None,
        cert=os.getenv("X509_USER_PROXY") or None,
        verifypeer=_env_bool("DBS_VERIFY_PEER", True),
        debug=1 if _env_bool("DBS_DEBUG", False) else 0,
        ca_info=os.getenv("X509_CERT_DIR") or None,
        userAgent=os.getenv("DBS_USER_AGENT", "dbs-mcp"),
        port=_env_int("DBS_PORT", 8443),
        accept=os.getenv("DBS_ACCEPT", "application/json"),
        aggregate=_env_bool("DBS_AGGREGATE", True),
        useGzip=_env_bool("DBS_USE_GZIP", False),
    )
    
    return dbs_client


def _public_methods() -> dict[str, Any]:
    client = _dbs_client()
    methods: dict[str, Any] = {}
    for name in dir(client):
        if name.startswith("_") or name in BLOCKED_METHODS:
            continue
        attr = getattr(client, name)
        if callable(attr):
            methods[name] = attr
    return methods


def _get_method(name: str) -> Any:
    methods = _public_methods()
    try:
        return methods[name]
    except KeyError as exc:
        available = ", ".join(sorted(methods))
        raise ValueError(f"Unsupported DBS method {name!r}. Available methods: {available}") from exc


def _call_dbs_method(method_name: str, kwargs: dict[str, Any] | None = None, payload: Any = None) -> Any:
    method = _get_method(method_name)
    kwargs = kwargs or {}

    try:
        if payload is not None:
            if method_name == "insertFiles":
                result = method(payload, **kwargs)
            elif kwargs:
                raise ValueError("Use either `payload` for object-style calls or `kwargs` for parameter calls, not both.")
            else:
                result = method(payload)
        else:
            result = method(**kwargs)
        return result

    except Exception as e:
        client = getattr(method, '__self__', None)
        if client is not None:
            http_resp = getattr(client, 'http_response', None)
            if http_resp is not None:
                status  = getattr(http_resp, 'status',  'N/A')
                reason  = getattr(http_resp, 'reason',  'N/A')
                body    = getattr(http_resp, 'data',    None) \
                       or getattr(http_resp, 'read',    None)
                print(f"[DBS DEBUG] method   : {method_name}",        flush=True)
                print(f"[DBS DEBUG] kwargs   : {kwargs}",             flush=True)
                print(f"[DBS DEBUG] status   : {status} {reason}",    flush=True)
                print(f"[DBS DEBUG] body     : {body!r}",             flush=True)
            else:
                print(f"[DBS DEBUG] http_response attribute was None on client", flush=True)
        else:
            print(f"[DBS DEBUG] Could not retrieve client from method {method_name}", flush=True)
        raise


@mcp.tool()
def dbs_server_info() -> Any:
    """Return metadata from the configured DBS server."""
    return _dbs_client().serverinfo()


@mcp.tool()
def dbs_list_methods() -> list[dict[str, str]]:
    """List public DBS client methods exposed by this MCP server."""
    items = []
    for name, method in sorted(_public_methods().items()):
        summary = inspect.getdoc(method) or ""
        items.append({"name": name, "summary": summary.splitlines()[0] if summary else ""})
    return items


@mcp.tool()
def dbs_method_help(method: str) -> dict[str, str]:
    """Return the local Python DBS client documentation for a method."""
    dbs_method = _get_method(method)
    return {
        "method": method,
        "doc": inspect.getdoc(dbs_method) or "",
    }


@mcp.tool()
def dbs_call(method: str, kwargs: dict[str, Any] | None = None, payload: Any = None) -> Any:
    """Call any public method on dbs.apis.dbsClient.DbsApi.

    Use `kwargs` for parameter-style DBS methods such as `listDatasets` or
    `updateFileStatus`. Use `payload` for object-style methods such as
    `insertDataset`, `insertBulkBlock`, `submitMigration`, and
    `removeMigration`.
    """
    try: 
        return _call_dbs_method(method, kwargs=kwargs, payload=payload)
    except Exception:
        import traceback
        traceback.print_exc()
        raise


@mcp.tool()
def dbs_list_datasets(
    dataset: str | None = None,
    primary_ds_name: str | None = None,
    processed_ds_name: str | None = None,
    data_tier_name: str | None = None,
    dataset_access_type: str | None = None,
    run_num: int | str | list[Any] | None = None,
    detail: bool = False,
) -> Any:
    """List DBS datasets with common filters."""
    kwargs = _drop_none(
        {
            "dataset": dataset,
            "primary_ds_name": primary_ds_name,
            "processed_ds_name": processed_ds_name,
            "data_tier_name": data_tier_name,
            "dataset_access_type": dataset_access_type,
            "run_num": run_num,
            "detail": detail,
        }
    )
    return _dbs_client().listDatasets(**kwargs)


@mcp.tool()
def dbs_list_files(
    dataset: str | None = None,
    block_name: str | None = None,
    logical_file_name: str | None = None,
    run_num: int | str | list[Any] | None = None,
    detail: bool = False,
    validFileOnly: int | None = None,
) -> Any:
    """List DBS files with common filters."""
    kwargs = _drop_none(
        {
            "dataset": dataset,
            "block_name": block_name,
            "logical_file_name": logical_file_name,
            "run_num": run_num,
            "detail": detail,
            "validFileOnly": validFileOnly,
        }
    )
    return _dbs_client().listFiles(**kwargs)


@mcp.tool()
def dbs_list_blocks(
    dataset: str | None = None,
    block_name: str | None = None,
    data_tier_name: str | None = None,
    logical_file_name: str | None = None,
    run_num: int | str | list[Any] | None = None,
    detail: bool = False,
) -> Any:
    """List DBS blocks with common filters."""
    kwargs = _drop_none(
        {
            "dataset": dataset,
            "block_name": block_name,
            "data_tier_name": data_tier_name,
            "logical_file_name": logical_file_name,
            "run_num": run_num,
            "detail": detail,
        }
    )
    return _dbs_client().listBlocks(**kwargs)


@mcp.tool()
def dbs_list_runs(
    dataset: str | None = None,
    block_name: str | None = None,
    logical_file_name: str | None = None,
    run_num: int | str | list[Any] | None = None,
) -> Any:
    """List run numbers for a dataset, block, file, or explicit run filter."""
    kwargs = _drop_none(
        {
            "dataset": dataset,
            "block_name": block_name,
            "logical_file_name": logical_file_name,
            "run_num": run_num,
        }
    )
    return _dbs_client().listRuns(**kwargs)


@mcp.tool()
def dbs_block_dump(block_name: str) -> Any:
    """Return all DBS information related to a block."""
    return _dbs_client().blockDump(block_name=block_name)


def _drop_none(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def main() -> None:
    mcp.run(
        transport="streamable-http",
    )


if __name__ == "__main__":
    main()
