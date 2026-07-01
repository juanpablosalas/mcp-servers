# DBS MCP Server

This is a Model Context Protocol server for the CMS Data Bookkeeping Service
(DBS), built on top of the official Python DBS client from
https://github.com/dmwm/DBSClient.

It exposes a focused set of common DBS read tools, plus a generic method caller
that can reach any public method on `dbs.apis.dbsClient.DbsApi`.

## Tools

- `dbs_server_info`: return DBS server metadata.
- `dbs_list_methods`: list public DBS client methods available through the MCP.
- `dbs_method_help`: return the local Python docstring for a DBS client method.
- `dbs_call`: call any public DBS client method by name.
- `dbs_list_datasets`: convenience wrapper for `listDatasets`.
- `dbs_list_files`: convenience wrapper for `listFiles`.
- `dbs_list_blocks`: convenience wrapper for `listBlocks`.
- `dbs_list_runs`: convenience wrapper for `listRuns`.
- `dbs_block_dump`: convenience wrapper for `blockDump`.

## Configuration

The server reads configuration from environment variables:

- `DBS_URL`: DBS service URL. Defaults to
  `https://cmsweb.cern.ch/dbs/prod/global/DBSReader/`.
- `DBS_PROXY`: optional SOCKS5 proxy URL.
- `X509_USER_CERT`: optional path to a user certificate.
- `X509_USER_KEY`: optional path to a private key.
- `X509_CERT_DIR`: optional CA certificate directory, passed to DBS as
  `ca_info`.
- `DBS_VERIFY_PEER`: set to `0`, `false`, or `no` to disable peer
  verification.
- `DBS_USER_AGENT`: optional suffix for the DBS client user agent.
- `DBS_PORT`: port added by the DBS client when the URL omits one. Defaults to
  `8443`.
- `DBS_ACCEPT`: response accept header. Defaults to `application/json`.
- `DBS_AGGREGATE`: set to `0`, `false`, or `no` to disable DBS client
  aggregation helpers.
- `DBS_USE_GZIP`: set to `1`, `true`, or `yes` to gzip POST bodies.
- `DBS_DEBUG`: set to `1`, `true`, or `yes` to print DBS HTTP debug output.

Read-only DBS endpoints often work with the default reader URL. Write/update
operations generally require valid CERN X.509 credentials.

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

`dbs3-client` depends on libcurl through `dbs3-pycurl`. If installation fails
while building pycurl, install libcurl development headers for your platform and
retry.

## Run

```bash
DBS_URL=https://cmsweb.cern.ch/dbs/prod/global/DBSReader/ dbs-mcp
```

The server uses stdio transport, which is what desktop MCP clients expect.

## Example MCP Client Configuration

```json
{
  "mcpServers": {
    "dbs": {
      "command": "/absolute/path/to/this/repo/.venv/bin/dbs-mcp",
      "env": {
        "DBS_URL": "https://cmsweb.cern.ch/dbs/prod/global/DBSReader/"
      }
    }
  }
}
```

## Generic Call Examples

List datasets:

```json
{
  "method": "listDatasets",
  "kwargs": {
    "dataset": "/Primary/Processed/TIER",
    "detail": true
  }
}
```

Insert or update calls can be made through `dbs_call` too, but only use them
against the intended DBS writer/migration service URL and with proper X.509
credentials.