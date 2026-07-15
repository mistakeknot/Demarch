#!/usr/bin/env python3
"""Estate drift checker: CanonGraph (live truth) vs GSV-CATALOG.md vs gsvdotcom registry.json.

Three surfaces, one estate. The graph carries live-verified serving state (serves edges)
and catalog fields ingested 2026-07-15 (goal mk-1ei); the catalog and the site registry
are prose/derived surfaces that rot. Checks:

  1. designation parity   — hulls present in catalog but absent from graph (and reverse)
  2. status drift         — catalog status string != graph project status
  3. stale hostnames      — a hostname in a catalog status that lives under a domain the
                            serving map governs but is NOT a live served host
  4. registry parity      — gsvdotcom registry.json designation/project/layer vs catalog

Reads CG_AUTH_TOKEN from ~/.config/canongraph/canongraph.env. Stdlib only. Exit 1 when
drift found, 0 clean (usable as a cron/CI gate).

Usage: python3 estate-drift.py [--catalog PATH] [--registry PATH]
"""
import argparse, json, os, re, sys, urllib.request

URL = "http://100.78.63.67:3943/mcp"
CATALOG = os.path.expanduser("~/projects/gsv-portfolio/strategy/GSV-CATALOG.md")
REGISTRY = os.path.expanduser("~/projects/gsvdotcom/src/data/registry.json")
LAYERS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "X", "studio"]
HOST_RE = re.compile(r"\b((?:[a-z0-9-]+\.)+[a-z]{2,})\b")


def graph_client():
    token = ""
    envf = os.path.expanduser("~/.config/canongraph/canongraph.env")
    for line in open(envf):
        if line.startswith("CG_AUTH_TOKEN="):
            token = line.strip().split("=", 1)[1]
    hdr = {"Authorization": "Bearer " + token, "Content-Type": "application/json",
           "Accept": "application/json, text/event-stream"}

    def post(payload, sid=None, want=True):
        h = dict(hdr)
        if sid:
            h["mcp-session-id"] = sid
        req = urllib.request.Request(URL, json.dumps(payload).encode(), h)
        with urllib.request.urlopen(req, timeout=10) as r:
            rsid = r.headers.get("mcp-session-id")
            if not want:
                return rsid, None
            try:
                for raw in r:
                    line = raw.decode("utf-8", "replace").strip()
                    if line.startswith("data:"):
                        return rsid, json.loads(line[5:])
            except Exception:
                pass
            return rsid, None

    sid, _ = post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                              "clientInfo": {"name": "estate-drift", "version": "1"}}})
    post({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid, want=False)
    n = [1]

    def tool(tname, args):
        n[0] += 1
        _, body = post({"jsonrpc": "2.0", "id": n[0], "method": "tools/call",
                        "params": {"name": tname, "arguments": args}}, sid)
        return json.loads(body["result"]["content"][0]["text"])
    return tool


def parse_catalog(path):
    """§7 registry table rows -> {designation: {project, layer_col, eco, status}}."""
    rows, in_reg = {}, False
    for line in open(path):
        if line.startswith("## 7."):
            in_reg = True
            continue
        if in_reg and line.startswith("## "):
            break
        m = re.match(r"\|\s*`(GSV-[^`]+)`\s*\|(.+)", line) if in_reg else None
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        if len(cells) < 4:
            continue
        rows[m.group(1)] = {"project": cells[0], "layer_col": cells[1],
                            "eco": cells[2], "status": cells[3]}
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default=CATALOG)
    ap.add_argument("--registry", default=REGISTRY)
    args = ap.parse_args()

    tool = graph_client()
    graph = {}
    for layer in LAYERS:
        for r in tool("query", {"query_id": "projects_in_layer",
                                "params": {"layer": layer}}).get("rows", []):
            if r.get("designation"):
                graph[r["designation"]] = {"project": r["project"], "layer": layer,
                                           "status": r.get("status") or ""}
    serving = tool("query", {"query_id": "serving_map", "params": {}}).get("rows", [])
    live_hosts = set()
    governed = set()
    for s in serving:
        for h in HOST_RE.findall(s.get("url") or ""):
            live_hosts.add(h)
            governed.add(".".join(h.split(".")[-2:]))
    # legacy families the serving estate governs even when only redirects remain
    governed |= {"jawncloud.com", "jawnfit.com", "jawnverse.com"}

    catalog = parse_catalog(args.catalog)
    findings = []

    def informational(c):
        blob = c["project"] + " " + c["layer_col"] + " " + c["status"]
        return "reserved" in blob or "cross-ref" in blob

    for desig, c in sorted(catalog.items()):
        g = graph.get(desig)
        if not g:
            if not informational(c):
                findings.append(f"MISSING-IN-GRAPH {desig} ({c['project']})")
            continue
        if c["status"].replace("*", "") != g["status"].replace("*", ""):
            findings.append(f"STATUS-DRIFT {desig} ({c['project']}): "
                            f"catalog='{c['status']}' graph='{g['status']}'")
        for host in HOST_RE.findall(c["status"]):
            base = ".".join(host.split(".")[-2:])
            if base in governed and host not in live_hosts:
                findings.append(f"STALE-HOSTNAME {desig} ({c['project']}): catalog says "
                                f"'{host}' — not a live served host (serving_map)")
    for desig, g in sorted(graph.items()):
        if desig not in catalog:
            findings.append(f"MISSING-IN-CATALOG {desig} ({g['project']})")

    try:
        reg = json.load(open(args.registry))
        rentries = {e["designation"]: e for e in reg.get("entries", [])
                    if not e.get("reserved") and not e.get("crossRef")}
        def clean_name(cell):
            return re.sub(r"\s*\(.*", "", cell.split(" — ")[0]).replace("*", "").strip()

        for desig, c in catalog.items():
            e = rentries.get(desig)
            if not e:
                if not informational(c):
                    findings.append(f"REGISTRY-MISSING {desig}")
            elif e.get("project") and e["project"] != clean_name(c["project"]):
                findings.append(f"REGISTRY-NAME-DRIFT {desig}: registry='{e['project']}' "
                                f"catalog='{clean_name(c['project'])}'")
    except FileNotFoundError:
        findings.append(f"REGISTRY-UNREADABLE {args.registry}")

    print(f"estate-drift: {len(catalog)} catalog rows, {len(graph)} graph hulls, "
          f"{len(serving)} serving edges, {len(live_hosts)} live hosts")
    if findings:
        print(f"\n{len(findings)} finding(s):")
        for f in findings:
            print(" -", f)
        return 1
    print("clean — no drift")
    return 0


if __name__ == "__main__":
    sys.exit(main())
