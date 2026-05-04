#!/usr/bin/env python3
"""
HackerOne MCP Server
Fetches program scope, guidelines, rewards, and more directly into Claude Desktop.

Usage:
  1. Set H1_USERNAME and H1_API_TOKEN env vars (or use .env file)
  2. Add to claude_desktop_config.json
  3. Ask Claude: "Show me the scope for shopify on HackerOne"
"""

import os
import json
import httpx
from typing import Optional
from mcp.server.fastmcp import FastMCP

# ── Init ──────────────────────────────────────────────────────────────────────
mcp = FastMCP("HackerOne")

H1_BASE = "https://api.hackerone.com/v1"

def get_auth() -> tuple[str, str]:
    username = os.environ.get("H1_USERNAME", "")
    token    = os.environ.get("H1_API_TOKEN", "")
    if not username or not token:
        raise ValueError(
            "Missing H1_USERNAME or H1_API_TOKEN env vars. "
            "Get your API token at: https://hackerone.com/settings/api_token/edit"
        )
    return (username, token)

def h1_get(path: str, params: dict = {}) -> dict:
    """Authenticated GET against H1 API."""
    r = httpx.get(
        f"{H1_BASE}{path}",
        params=params,
        auth=get_auth(),
        headers={"Accept": "application/json"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()

def fmt_bounty(b: dict) -> str:
    if not b:
        return "Not specified"
    low  = b.get("low_label")  or b.get("low")
    high = b.get("high_label") or b.get("high")
    if low and high:
        return f"${low} – ${high}"
    if high:
        return f"Up to ${high}"
    return "Varies"

# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_program(handle: str) -> str:
    """
    Fetch full details for a HackerOne program by its handle.
    Returns policy, scope summary, submission state, response times, and stats.

    Args:
        handle: Program handle (e.g. 'shopify', 'github', 'twitter')
    """
    try:
        data = h1_get(f"/hackers/programs/{handle}")
        attrs = data.get("attributes", {})
        rels  = data.get("relationships", {})

        # Basic info
        name        = attrs.get("name", handle)
        state       = attrs.get("submission_state", "unknown")
        offers_bounty = attrs.get("offers_bounties", False)
        policy      = attrs.get("policy", "No policy text available.")
        started     = attrs.get("started_accepting_at", "unknown")
        url         = f"https://hackerone.com/{handle}"

        # Response SLAs
        ttr  = attrs.get("average_time_to_first_response_in_days_last_quarter")
        ttb  = attrs.get("average_time_to_bounty_in_days_last_quarter")
        ttre = attrs.get("average_time_to_resolution_in_days_last_quarter")

        # Stats
        reports_resolved = attrs.get("resolved_report_count", "N/A")
        thanks = attrs.get("thank_count", "N/A")
        total_bounties = attrs.get("total_bounties_paid_prefix", "") + \
                         str(attrs.get("total_bounties_paid", "N/A"))

        lines = [
            f"# 🎯 {name}",
            f"**URL**: {url}",
            f"**Submission State**: {state.replace('_', ' ').title()}",
            f"**Bounties**: {'Yes 💰' if offers_bounty else 'No (VDP)'}",
            f"**Total Paid Out**: {total_bounties}",
            f"**Accepting since**: {started}",
            "",
            "## ⏱ Response Times (Last Quarter)",
            f"- First Response: {ttr or 'N/A'} days",
            f"- Time to Bounty:  {ttb or 'N/A'} days",
            f"- Time to Resolve: {ttre or 'N/A'} days",
            "",
            "## 📊 Stats",
            f"- Reports Resolved: {reports_resolved}",
            f"- Researchers Thanked: {thanks}",
            "",
            "## 📋 Policy",
            policy[:3000] + ("..." if len(policy) > 3000 else ""),
        ]
        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"❌ Program '{handle}' not found on HackerOne. Check the handle spelling."
        return f"❌ API Error {e.response.status_code}: {e.response.text[:300]}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


@mcp.tool()
def get_scope(handle: str) -> str:
    """
    Fetch the full in-scope and out-of-scope targets for a HackerOne program.
    Shows asset type, identifier, bounty eligibility, severity, and instructions.

    Args:
        handle: Program handle (e.g. 'shopify', 'github', 'nordvpn')
    """
    try:
        data = h1_get(f"/hackers/programs/{handle}/structured_scopes",
                      {"page[size]": 100})

        in_scope  = []
        out_scope = []

        for item in data.get("data", []):
            a = item.get("attributes", {})
            entry = {
                "type":         a.get("asset_type", "unknown"),
                "identifier":   a.get("asset_identifier", ""),
                "eligible":     a.get("eligible_for_bounty", False),
                "eligible_sub": a.get("eligible_for_submission", True),
                "max_severity": a.get("max_severity", ""),
                "instructions": a.get("instruction", ""),
            }
            if a.get("eligible_for_submission", True):
                in_scope.append(entry)
            else:
                out_scope.append(entry)

        def fmt_entry(e: dict) -> str:
            bounty_tag = "💰" if e["eligible"] else "🔵"
            sev = f" | Max: **{e['max_severity']}**" if e["max_severity"] else ""
            note = f"\n  > {e['instructions'][:200]}" if e["instructions"] else ""
            return f"- {bounty_tag} `{e['identifier']}` ({e['type']}){sev}{note}"

        lines = [f"# 🎯 Scope — {handle}",
                 f"_(💰 = bounty eligible | 🔵 = submission only)_", ""]

        if in_scope:
            lines.append(f"## ✅ In Scope ({len(in_scope)} targets)")
            for e in in_scope:
                lines.append(fmt_entry(e))
        else:
            lines.append("## ✅ In Scope\n_No structured scope defined._")

        lines.append("")

        if out_scope:
            lines.append(f"## ❌ Out of Scope ({len(out_scope)} targets)")
            for e in out_scope:
                lines.append(f"- `{e['identifier']}` ({e['type']})")

        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"❌ Program '{handle}' not found."
        return f"❌ API Error {e.response.status_code}: {e.response.text[:300]}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


@mcp.tool()
def get_bounties(handle: str) -> str:
    """
    Fetch the bounty table for a HackerOne program — shows payout ranges
    by severity (critical, high, medium, low) per asset type.

    Args:
        handle: Program handle (e.g. 'shopify', 'twitter')
    """
    try:
        data  = h1_get(f"/hackers/programs/{handle}/structured_scopes",
                       {"page[size]": 100})
        attrs_prog = h1_get(f"/hackers/programs/{handle}").get("attributes", {})

        if not attrs_prog.get("offers_bounties", False):
            return f"ℹ️ **{handle}** is a Vulnerability Disclosure Program (VDP) — no monetary bounties."

        seen = {}
        for item in data.get("data", []):
            a = item.get("attributes", {})
            if not a.get("eligible_for_bounty"):
                continue
            asset_type = a.get("asset_type", "OTHER")
            bounties   = a.get("bounties", {})
            if bounties and asset_type not in seen:
                seen[asset_type] = bounties

        lines = [f"# 💰 Bounty Table — {handle}", ""]

        if not seen:
            # Fallback: show program-level bounty ranges if structured not available
            lines.append("_Structured per-severity bounties not exposed via API._")
            lines.append("")
            lines.append(f"**Profile URL**: https://hackerone.com/{handle}")
            lines.append("Check the program page directly for the bounty table.")
            return "\n".join(lines)

        for asset_type, b in seen.items():
            lines.append(f"## {asset_type}")
            lines.append(f"| Severity | Range |")
            lines.append(f"|----------|-------|")
            for sev in ["critical", "high", "medium", "low", "none"]:
                if sev in b:
                    entry = b[sev]
                    lo = entry.get("low_label")  or entry.get("low",  "")
                    hi = entry.get("high_label") or entry.get("high", "")
                    rng = f"${lo} – ${hi}" if lo and hi else (f"Up to ${hi}" if hi else "N/A")
                    lines.append(f"| {sev.capitalize()} | {rng} |")
            lines.append("")

        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"❌ Program '{handle}' not found."
        return f"❌ API Error {e.response.status_code}: {e.response.text[:300]}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


@mcp.tool()
def list_programs(
    page: int = 1,
    bounties_only: bool = False,
    keyword: Optional[str] = None
) -> str:
    """
    List public HackerOne bug bounty programs. Supports filtering by bounty
    eligibility and keyword search in program name.

    Args:
        page: Page number (default 1, 25 results per page)
        bounties_only: If True, only show programs that offer monetary bounties
        keyword: Filter programs whose name contains this string (case-insensitive)
    """
    try:
        params = {
            "page[number]": page,
            "page[size]": 25,
        }
        data = h1_get("/hackers/programs", params)

        programs = data.get("data", [])
        meta     = data.get("meta", {})
        total    = meta.get("total_count", "?")

        if bounties_only:
            programs = [p for p in programs if p.get("attributes", {}).get("offers_bounties")]
        if keyword:
            kw = keyword.lower()
            programs = [p for p in programs
                        if kw in p.get("attributes", {}).get("name", "").lower()
                        or kw in p.get("id", "").lower()]

        lines = [
            f"# 📋 HackerOne Programs — Page {page}",
            f"Total programs: {total} | Showing: {len(programs)}",
            "",
        ]

        for p in programs:
            a      = p.get("attributes", {})
            handle = p.get("id", "")
            name   = a.get("name", handle)
            state  = a.get("submission_state", "")
            bounty = "💰" if a.get("offers_bounties") else "🔵 VDP"
            open_  = "✅ Open" if state == "open" else "🔒 Invite-only" if state == "soft_launched" else state

            lines.append(f"### {name} (`{handle}`)")
            lines.append(f"{bounty} | {open_}")
            lines.append(f"→ `get_program('{handle}')` or `get_scope('{handle}')`")
            lines.append("")

        if not programs:
            lines.append("_No programs matched your filter._")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Error: {str(e)}"


@mcp.tool()
def search_program(query: str) -> str:
    """
    Search for HackerOne programs by name or handle keyword.
    Returns top matches with their key details.

    Args:
        query: Search term (e.g. 'shopify', 'crypto', 'vpn')
    """
    try:
        # Fetch a larger set and filter
        data     = h1_get("/hackers/programs", {"page[size]": 100})
        programs = data.get("data", [])
        q        = query.lower()

        matches = [
            p for p in programs
            if q in p.get("attributes", {}).get("name", "").lower()
            or q in p.get("id", "").lower()
        ]

        if not matches:
            return f"🔍 No programs found matching **'{query}'** in the first 100 results.\n\nTry `list_programs(keyword='{query}')` or check https://hackerone.com/programs"

        lines = [f"# 🔍 Search Results: '{query}'", f"Found {len(matches)} match(es)", ""]

        for p in matches[:15]:
            a      = p.get("attributes", {})
            handle = p.get("id", "")
            name   = a.get("name", handle)
            state  = a.get("submission_state", "unknown")
            bounty = "💰 Bounty" if a.get("offers_bounties") else "🔵 VDP"
            open_  = "✅ Open" if state == "open" else "🔒 Invite-only"
            ttr    = a.get("average_time_to_first_response_in_days_last_quarter")

            lines.append(f"## {name} (`{handle}`)")
            lines.append(f"**Type**: {bounty} | **Status**: {open_}")
            if ttr:
                lines.append(f"**Avg first response**: {ttr} days")
            lines.append(f"**Profile**: https://hackerone.com/{handle}")
            lines.append(f"→ Run `get_scope('{handle}')` or `get_bounties('{handle}')`")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Error: {str(e)}"


@mcp.tool()
def get_program_guidelines(handle: str) -> str:
    """
    Extract the program guidelines / rules of engagement from HackerOne policy text.
    Pulls out key sections: what's allowed, what's NOT allowed, disclosure policy,
    safe harbor, and testing rules.

    Args:
        handle: Program handle (e.g. 'shopify', 'grab', 'twitter')
    """
    try:
        data  = h1_get(f"/hackers/programs/{handle}")
        attrs = data.get("attributes", {})
        name  = attrs.get("name", handle)
        policy = attrs.get("policy", "")

        if not policy:
            return f"ℹ️ **{name}** has no published policy text via API.\nVisit: https://hackerone.com/{handle}"

        # Pull out key sections intelligently
        lines = [
            f"# 📜 Guidelines — {name}",
            f"Source: https://hackerone.com/{handle}",
            "",
        ]

        # Heuristic section keywords to highlight
        section_keywords = {
            "In Scope":          ["in scope", "in-scope", "inscope"],
            "Out of Scope":      ["out of scope", "out-of-scope"],
            "Allowed Testing":   ["allowed", "permitted", "you may", "you can"],
            "Prohibited":        ["not allowed", "prohibited", "do not", "don't", "forbidden"],
            "Safe Harbor":       ["safe harbor", "legal", "prosecution", "won't take"],
            "Disclosure Policy": ["disclosure", "public", "publish", "coordinate"],
            "Rewards":           ["reward", "bounty", "payment", "payout"],
        }

        # Just display the full policy nicely truncated — it's markdown from H1
        max_len = 4000
        display = policy if len(policy) <= max_len else policy[:max_len] + \
                  f"\n\n_...truncated. Full policy at https://hackerone.com/{handle}_"

        lines.append(display)
        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"❌ Program '{handle}' not found."
        return f"❌ API Error {e.response.status_code}: {e.response.text[:300]}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


@mcp.tool()
def get_my_reports(
    state: str = "all",
    page: int = 1
) -> str:
    """
    Fetch YOUR submitted HackerOne reports (requires your API token).
    Filter by state to track triaged, bounty-awarded, or pending reports.

    Args:
        state: Filter by state — 'all', 'new', 'triaged', 'resolved',
               'bounty-awarded', 'informative', 'duplicate', 'not-applicable'
        page:  Page number (default 1)
    """
    try:
        params: dict = {"page[number]": page, "page[size]": 25}
        if state != "all":
            params["filter[state][]"] = state

        data    = h1_get("/hackers/me/reports", params)
        reports = data.get("data", [])
        meta    = data.get("meta", {})
        total   = meta.get("total_count", "?")

        lines = [
            f"# 📬 My Reports — State: {state} | Page {page}",
            f"Total: {total}",
            "",
        ]

        if not reports:
            lines.append("_No reports found for this filter._")
            return "\n".join(lines)

        for r in reports:
            a       = r.get("attributes", {})
            rid     = r.get("id", "")
            title   = a.get("title", "Untitled")
            rstate  = a.get("state", "")
            created = a.get("created_at", "")[:10]
            bounty  = a.get("bounty_amount")
            prog    = r.get("relationships", {}).get("program", {}).get("data", {}).get("id", "?")

            state_emoji = {
                "new": "🆕", "triaged": "🔬", "resolved": "✅",
                "bounty-awarded": "💰", "informative": "ℹ️",
                "duplicate": "🔁", "not-applicable": "❌"
            }.get(rstate, "❓")

            lines.append(f"### #{rid} — {title}")
            lines.append(f"{state_emoji} **{rstate}** | Program: `{prog}` | Submitted: {created}")
            if bounty:
                lines.append(f"💰 Bounty: ${bounty}")
            lines.append(f"🔗 https://hackerone.com/reports/{rid}")
            lines.append("")

        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return "❌ Unauthorized — check your H1_USERNAME and H1_API_TOKEN."
        return f"❌ API Error {e.response.status_code}: {e.response.text[:300]}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


@mcp.tool()
def get_my_profile() -> str:
    """
    Fetch your own HackerOne hacker profile — reputation, signal, impact,
    rank, and submission stats.
    """
    try:
        data  = h1_get("/hackers/me")
        attrs = data.get("attributes", {})

        username  = attrs.get("username", "unknown")
        rep       = attrs.get("reputation", 0)
        signal    = attrs.get("signal", 0.0)
        impact    = attrs.get("impact", 0.0)
        rank      = attrs.get("rank", "N/A")
        bio       = attrs.get("bio", "")
        website   = attrs.get("website", "")

        lines = [
            f"# 👤 HackerOne Profile: @{username}",
            f"**Profile**: https://hackerone.com/{username}",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Reputation | {rep} |",
            f"| Signal | {signal:.2f} |",
            f"| Impact | {impact:.2f} |",
            f"| Rank | {rank} |",
        ]

        if bio:
            lines += ["", f"**Bio**: {bio}"]
        if website:
            lines += [f"**Website**: {website}"]

        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return "❌ Unauthorized — check your H1_USERNAME and H1_API_TOKEN."
        return f"❌ API Error {e.response.status_code}: {e.response.text[:300]}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 HackerOne MCP Server starting (stdio mode)...")
    mcp.run(transport="stdio")
