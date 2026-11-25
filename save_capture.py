"""Read-only inspection of offline VIctory save data."""
import hashlib
import re
import stat


BLOCK = 64 * 1024


def inspect_file(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while block := stream.read(BLOCK):
            size += len(block)
            digest.update(block)
    return {"file": path.name, "bytes": size, "sha256": digest.hexdigest()}


def victory_manifest(path):
    """Decode logical names from one VIctory version's binary manifest."""
    data = path.read_bytes()
    offset = 0
    names = []
    while offset < len(data):
        if len(data) - offset < 4:
            raise ValueError(f"Incomplete string length at byte {offset}")
        size = int.from_bytes(data[offset:offset + 4], "little")
        offset += 4
        if size > len(data) - offset:
            raise ValueError(f"Incomplete string at byte {offset}")
        names.append(data[offset:offset + size].decode("utf-8"))
        offset += size
    if len(names) < 2:
        raise ValueError("Manifest requires container and display names")
    return {"container": names[0], "display": names[1],
            "blobs": [{"name": name, "file": str(i)} for i, name in enumerate(names[2:])]}


def identifier(text):
    return hashlib.sha256(text.encode("utf-8", errors="surrogatepass")).hexdigest()


def entry_kind(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return "missing"
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        return "link"
    if stat.S_ISREG(info.st_mode):
        return "file"
    if stat.S_ISDIR(info.st_mode):
        return "directory"
    return "special"


def inspect_version(path):
    version = {"version": path.name, "status": "incomplete", "blobs": {}}
    kind = entry_kind(path)
    if kind != "directory":
        return {**version, "problem": f"version:{kind}"}
    manifest_path = path / "manifest"
    kind = entry_kind(manifest_path)
    if kind != "file":
        return {**version, "problem": f"manifest:{kind}"}
    try:
        manifest = victory_manifest(manifest_path)
    except ValueError:
        return {**version, "problem": "manifest:malformed"}
    version["container_id"] = identifier(manifest["container"])
    complete = True
    for blob in manifest["blobs"]:
        key = identifier(blob["name"])
        if key in version["blobs"]:
            return {**version, "problem": "manifest:duplicate_name"}
        file = path / blob["file"]
        kind = entry_kind(file)
        if kind == "file":
            record = inspect_file(file)
        else:
            complete = False
            record = {"file": blob["file"], "problem": kind}
        version["blobs"][key] = record
    version["status"] = "complete" if complete else "incomplete"
    return version


def newest_complete(versions):
    return next((version for version in versions if version["status"] == "complete"), None)


def inventory(root):
    if entry_kind(root) != "directory":
        raise ValueError("Capture expects an offline directory")
    containers = {}
    pending = [root]
    while pending:
        parent = pending.pop()
        versions = []
        for path in sorted(parent.iterdir()):
            if re.fullmatch(r"v[1-9][0-9]{0,19}", path.name) and int(path.name[1:]) < 2**64:
                versions.append(inspect_version(path))
            elif not path.name.endswith((".new", ".gone")) and entry_kind(path) == "directory":
                pending.append(path)
        if versions:
            versions.sort(key=lambda v: int(v["version"][1:]), reverse=True)
            latest = newest_complete(versions)
            key = identifier(parent.relative_to(root).as_posix())
            containers[key] = {"latest_complete": latest["version"] if latest else None, "versions": versions}
    return containers


def capture(root, commit, previous):
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", commit):
        raise ValueError("Use a 7 to 40 digit hexadecimal VIctory commit ID")
    containers = inventory(root)
    report = {"format": 1, "victory_commit": commit.lower(), "containers": containers}
    if previous is None:
        return report
    before = inventory(previous)
    changes = []
    for key in sorted(before.keys() | containers.keys()):
        if key not in before or key not in containers:
            changes.append({"container": key, "change": "added" if key in containers else "removed"})
            continue
        old = newest_complete(before[key]["versions"])
        new = newest_complete(containers[key]["versions"])
        if old is None or new is None or old["container_id"] != new["container_id"]:
            changes.append({"container": key, "change": "not_comparable"})
            continue
        left, right = old["blobs"], new["blobs"]
        for blob in sorted(left.keys() | right.keys()):
            if blob not in left:
                change = "added"
            elif blob not in right:
                change = "removed"
            elif left[blob]["sha256"] != right[blob]["sha256"]:
                change = "modified"
            else:
                continue
            changes.append({"container": key, "blob": blob, "change": change})
    report["changes"] = changes
    return report
