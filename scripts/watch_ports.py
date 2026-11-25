"""Triage public issues, pull requests and releases via the authenticated gh CLI."""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path

SOURCES = Path(__file__).with_name("ports.json")
SAVE = re.compile(
    r"\b(save[ -]?(?:game|file|slot)s?|game[ -]?saves?|(?:save|load) game|"
    r"(?:saved|saving) (?:the |a )?game|load(?:ing)? (?:a |the )?save|"
    r"manual saves?|autosaves?)\b", re.I)
GAME = re.compile(r"\b(?:gta|grand theft auto)\s*(?:6|vi)\b", re.I)


def relevant(text, require_game_name):
    return bool(SAVE.search(text) and (not require_game_name or GAME.search(text)))


def gh(*args, body=None):
    result = subprocess.run(["gh", *args], input=body, capture_output=True,
                            encoding="utf-8", check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout


def pages(endpoint):
    return (item for page in json.loads(gh("api", "--paginate", "--slurp", endpoint))
            for item in page)


def candidates(repo, config, since):
    for kind, query in [
        ("issues", "state=all&per_page=100&since=" + since),
        ("releases", "per_page=100"),
    ]:
        for item in pages(f"repos/{repo}/{kind}?{query}"):
            stamp = item.get("updated_at") or item.get("published_at") or item.get("created_at")
            if not stamp or stamp < since:
                continue
            title = item.get("title") or item.get("name") or item.get("tag_name", "")
            if relevant(title + "\n" + (item.get("body") or ""), config["require_game_name"]):
                yield item["html_url"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true", help="Open triage issues in GITHUB_REPOSITORY")
    args = parser.parse_args()
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")
    target = os.environ["GITHUB_REPOSITORY"] if args.publish else None
    known = set()
    if target:
        for issue in pages(f"repos/{target}/issues?state=all&per_page=100"):
            if issue.get("user", {}).get("login") == "github-actions[bot]":
                known.update(re.findall(r"<!-- port-watch (https://github\.com/\S+) -->", issue.get("body") or ""))
    errors = []
    for repo, config in json.loads(SOURCES.read_text()).items():
        try:
            fresh = sorted(set(candidates(repo, config, since)) - known)
            for url in fresh:
                print(url)
            if target and fresh:
                title = f"Investigate save support in {repo}"
                links = "\n".join(f"- {url} <!-- port-watch {url} -->" for url in fresh)
                body = (f"{links}\n\nRecord the build, save a slot, restart the game and reload the same slot. "
                        f"Follow the [collection protocol](https://github.com/{target}/blob/main/docs/COLLECTION.md). "
                        "Classify the result as confirmed, inconclusive or a false positive.")
                gh("issue", "create", "--repo", target, "--title", title, "--body-file", "-", body=body)
        except RuntimeError as error:
            errors.append(f"{repo}: {error}")
    if errors:
        raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()
