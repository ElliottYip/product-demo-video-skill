#!/usr/bin/env python3
"""Capture evidence pages through the Codex Playwright CLI and update sources.json."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


DISMISS_JS = r"""async page => {
  const labels = ['Reject all','Reject All','Decline','Only necessary','Necessary only','拒绝全部','仅必要','不同意','关闭','Close','Dismiss','No thanks','Not now'];
  for (const label of labels) {
    const nodes = page.getByRole('button', {name: label, exact: false});
    if (await nodes.count()) { try { await nodes.first().click({timeout:800}); } catch {} }
  }
  await page.evaluate(() => {
    const selectors = ['[class*=cookie]','[id*=cookie]','[class*=chat]','[id*=chat]','[class*=intercom]','[aria-label*=chat i]'];
    for (const selector of selectors) for (const el of document.querySelectorAll(selector)) {
      const s = getComputedStyle(el); const r = el.getBoundingClientRect();
      if ((s.position === 'fixed' || s.position === 'sticky') && r.width * r.height > 2000) el.remove();
    }
  });
  await page.waitForTimeout(800);
}"""


def run(cli: str, session: str, *args: str) -> str:
    cmd = [cli, "--session", session, *args]
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True)
    if proc.returncode:
        raise RuntimeError(f"Playwright command failed: {' '.join(args[:2])}\n{proc.stderr or proc.stdout}")
    return proc.stdout


def js_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sources", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, default=Path("screenshots"))
    p.add_argument("--width", type=int, default=1440)
    p.add_argument("--height", type=int, default=1000)
    p.add_argument("--session", default="ai-product-capture")
    p.add_argument("--full-page", action="store_true")
    p.add_argument("--source-id", action="append", help="Capture only these source ids; repeat as needed")
    args = p.parse_args()

    cli = os.environ.get("PLAYWRIGHT_CLI") or str(Path.home() / ".codex/skills/playwright/scripts/playwright_cli.sh")
    if not Path(cli).exists():
        raise SystemExit("Set PLAYWRIGHT_CLI to the Codex Playwright wrapper")
    data = json.loads(args.sources.read_text(encoding="utf-8"))
    sources = data.get("sources", [])
    if args.source_id:
        wanted = set(args.source_id)
        sources = [s for s in sources if s.get("id") in wanted]
    if not sources:
        raise SystemExit("sources.json has no sources")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run(cli, args.session, "open", sources[0]["url"])
    run(cli, args.session, "resize", str(args.width), str(args.height))
    try:
        for src in sources:
            run(cli, args.session, "open", src["url"])
            run(cli, args.session, "run-code", DISMISS_JS)
            if src.get("focus_text"):
                focus = json.dumps(str(src["focus_text"]), ensure_ascii=False)
                focus_js = f"async page => {{ const n=page.getByText({focus}, {{exact:false}}); if(await n.count()) {{ await n.first().scrollIntoViewIfNeeded(); await page.waitForTimeout(600); }} }}"
                run(cli, args.session, "run-code", focus_js)
            elif src.get("scroll_y") is not None:
                y = max(0, int(src["scroll_y"]))
                run(cli, args.session, "run-code", f"async page => {{ await page.evaluate(() => scrollTo(0,{y})); await page.waitForTimeout(600); }}")
            safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", src["id"])
            out = (args.output_dir / f"{safe}.png").resolve()
            shot_js = f"async page => await page.screenshot({{path:{js_quote(str(out))}, fullPage:{str(args.full_page).lower()}}})"
            run(cli, args.session, "run-code", shot_js)
            meta = run(cli, args.session, "eval", "JSON.stringify({title:document.title,url:location.href})")
            match = re.search(r'\{\\?"title\\?".*?\}', meta, re.S)
            if match:
                raw = match.group(0).replace('\\"', '"')
                try:
                    m = json.loads(raw)
                    src["title"] = m.get("title") or src.get("title", "")
                    src["final_url"] = m.get("url") or src["url"]
                except json.JSONDecodeError:
                    pass
            src["accessed_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
            src["screenshot"] = str(out)
            print(f"Captured {src['id']} -> {out}")
    finally:
        try:
            run(cli, args.session, "close")
        except Exception:
            pass
    args.sources.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
