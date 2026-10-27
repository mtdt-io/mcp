#!/usr/bin/env python3
"""Build and inspect MTDT catalog packages; no credentials or runtime tool calls."""

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import zipfile
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
ENDPOINT = "https://mcp.mtdt.io"
ICON = "assets/mtdt-icon.png"
SKILLS = ("mtdt-deploy", "mtdt-troubleshoot")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def https_url(value):
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.hostname) and not (
        parsed.username or parsed.password
    )


def inventory(path):
    value = read_json(path)
    if isinstance(value, list):
        return {}, value
    evidence = value.get("evidence", {})
    result = value.get("result", value)
    return evidence, result.get("tools", [])


def openai_manifest(demo_url=None):
    manifest = read_json(ROOT / "publishing/openai-plugin.json")
    review = manifest["extensions"]["com.openai"].setdefault("review", {})
    review["test_cases"] = read_json(ROOT / "publishing/review-cases.json")
    if demo_url:
        if not https_url(demo_url):
            raise ValueError("--demo-url must be an HTTPS URL without credentials")
        review["demo_recording_url"] = demo_url
    license_value = read_json(ROOT / ".claude-plugin/plugin.json").get("license")
    if license_value:
        manifest["license"] = license_value
    return manifest


def package_files(host, demo_url=None):
    files = {}
    for skill in SKILLS:
        directory = ROOT / "skills" / skill
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Skill files must not be symlinks: {path.relative_to(ROOT)}")
            if path.is_file():
                files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    # Maintainer submission instructions stay out of the distributed README.
    files["README.md"] = (ROOT / "README.md").read_text(encoding="utf-8").split(
        "\n## Directory packages\n", 1
    )[0].encode("utf-8")
    for relative in ("CONNECT.md", ICON, "LICENSE"):
        path = ROOT / relative
        if path.exists():
            if path.is_symlink():
                raise ValueError(f"Distribution file is a symlink: {relative}")
            files[relative] = path.read_bytes()
    if host == "openai":
        files[".codex-plugin/plugin.json"] = json_bytes(openai_manifest(demo_url))
        files[".mcp.json"] = json_bytes({"mcpServers": {"mtdt": {"url": ENDPOINT}}})
    else:
        files[".claude-plugin/plugin.json"] = (ROOT / ".claude-plugin/plugin.json").read_bytes()
        files[".mcp.json"] = (ROOT / ".mcp.json").read_bytes()
    return files


def validate_files(host, files):
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    manifest_path = f".{ 'codex' if host == 'openai' else 'claude' }-plugin/plugin.json"
    manifest = json.loads(files[manifest_path])
    require(bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", manifest.get("name", ""))), "Invalid plugin name")
    require(len(manifest.get("name", "")) <= 64, "Plugin name exceeds 64 characters")
    require(bool(re.fullmatch(r"\d+\.\d+\.\d+", manifest.get("version", ""))), "Invalid release version")
    require(bool(manifest.get("author", {}).get("name")), "Missing publisher name")
    require(0 < len(manifest.get("description", "")) <= 4000, "Invalid package description")
    mcp = json.loads(files[".mcp.json"])
    expected = {"url": ENDPOINT} if host == "openai" else {"type": "http", "url": ENDPOINT}
    require(mcp == {"mcpServers": {"mtdt": expected}}, "Unexpected MCP server config or extra credential/header")
    for name, data in files.items():
        path = PurePosixPath(name)
        require(not path.is_absolute() and ".." not in path.parts, f"Invalid archive path: {name}")
        require(len(data) <= 5 * 1024 * 1024, f"File exceeds 5 MiB: {name}")
        require(not name.startswith("publishing/"), "Submission instructions included in distribution")
        if name.endswith((".md", ".json")):
            text = data.decode("utf-8")
            require(not re.search(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|eyJ[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}", text), f"Possible credential in {name}")
            require(not any(token in text for token in ("${user_config.", "test_credentials", "reviewer_instructions")), f"Unsupported private/config field in {name}")
    for skill in SKILLS:
        text = files[f"skills/{skill}/SKILL.md"].decode("utf-8")
        require(text.startswith("---\n"), f"Missing skill frontmatter: {skill}")
        header = text.split("---", 2)[1]
        require(f"name: {skill}\n" in header, f"Skill name does not match directory: {skill}")
        description = re.search(r"^description: (.+)$", header, re.M)
        require(bool(description) and len(description.group(1)) <= 1024, f"Invalid skill description: {skill}")
    png = files.get(ICON, b"")
    require(png.startswith(b"\x89PNG\r\n\x1a\n") and len(png) >= 24, "Icon is not a PNG")
    if len(png) >= 24:
        width, height = struct.unpack(">II", png[16:24])
        require(48 <= width == height <= 4096, "Icon must be square, 48–4096 pixels")
        require(png.endswith(b"IEND\xaeB`\x82"), "Incomplete PNG")
    if host == "openai":
        interface = manifest.get("interface", {})
        for key, limit in (("displayName", 30), ("shortDescription", 30), ("longDescription", 4000), ("developerName", 80)):
            require(0 < len(interface.get(key, "")) <= limit, f"Invalid interface.{key}")
        require(bool(interface.get("category")), "Missing category")
        require(isinstance(interface.get("capabilities"), list) and len(interface["capabilities"]) <= 20, "Invalid capabilities")
        for key in ("websiteURL", "supportURL", "privacyPolicyURL", "termsOfServiceURL"):
            value = interface.get(key, "")
            require(https_url(value) and len(value) <= 1024, f"Invalid interface.{key}")
        prompts = interface.get("defaultPrompt", [])
        require(isinstance(prompts, list) and 1 <= len(prompts) <= 3 and all(len(p) <= 128 for p in prompts), "Invalid starter prompts")
        for key in ("composerIcon", "logo"):
            value = interface.get(key, "")
            require(value.startswith("./") and value[2:] in files, f"Missing asset for {key}")
        require(manifest.get("skills") == "./skills/", "Invalid skills directory")
        require(manifest.get("mcpServers") == "./.mcp.json", "Invalid MCP component path")
        cases = manifest["extensions"]["com.openai"]["review"]["test_cases"]
        known = {t["name"] for t in inventory(ROOT / "publishing/tool-inventory.json")[1]}
        for kind, count in (("positive", 5), ("negative", 3)):
            require(len(cases.get(kind, [])) == count, f"Expected exactly {count} {kind} cases")
            for case in cases.get(kind, []):
                required = ("description", "prompt", "tools_triggered", "expected_behavior") if kind == "positive" else ("description", "prompt")
                require(all(case.get(k) for k in required), f"Incomplete {kind} case")
                triggered = {n.strip() for n in case.get("tools_triggered", "").split(",") if n.strip()}
                require(triggered <= known, f"Unknown review tools: {sorted(triggered - known)}")
    return errors


def build(args):
    DIST.mkdir(exist_ok=True)
    version = openai_manifest()["version"]
    checksums = []
    for host in ("openai", "claude"):
        files = package_files(host, args.demo_url)
        errors = validate_files(host, files)
        if errors:
            raise ValueError("; ".join(errors))
        staging = DIST / host
        if staging.exists():
            shutil.rmtree(staging)
        for name, data in files.items():
            path = staging / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        archive = DIST / f"mtdt-{host}-{version}.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for name, data in sorted(files.items()):
                entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                zip_file.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        checksums.append(f"{digest}  {archive.name}")
        print(f"Built {archive.relative_to(ROOT)} ({len(files)} files, {archive.stat().st_size} bytes)")
    (DIST / "SHA256SUMS").write_text("\n".join(checksums) + "\n", encoding="utf-8")


def check(_args):
    errors = []
    version = openai_manifest()["version"]
    claude = read_json(ROOT / ".claude-plugin/plugin.json")
    marketplace = read_json(ROOT / ".claude-plugin/marketplace.json")
    if claude["version"] != version or marketplace["plugins"][0]["version"] != version:
        errors.append("OpenAI/Claude/marketplace plugin versions do not match")
    for host in ("openai", "claude"):
        files = package_files(host)
        errors.extend(f"{host}: {e}" for e in validate_files(host, files))
        archive = DIST / f"mtdt-{host}-{version}.zip"
        if not archive.exists():
            errors.append(f"Build the missing archive: {archive.name}")
            continue
        with zipfile.ZipFile(archive) as zip_file:
            archived = {name: zip_file.read(name) for name in zip_file.namelist()}
            if len(archived) != len(zip_file.namelist()):
                errors.append(f"Duplicate ZIP entries: {host}")
            if zip_file.testzip():
                errors.append(f"Bad ZIP CRC: {host}")
            errors.extend(f"{host} ZIP: {e}" for e in validate_files(host, archived))
            # An optional real demo URL is the only build-time manifest override.
            if host == "openai":
                manifest = json.loads(archived[".codex-plugin/plugin.json"])
                demo = manifest["extensions"]["com.openai"]["review"].get("demo_recording_url")
                files = package_files(host, demo)
            if archived != files:
                errors.append(f"Archive differs from current source: rebuild {host}")
    if errors:
        raise ValueError("\n".join(errors))
    print("Package checks passed: both ZIPs, versions, assets, skills, cases and MCP configurations")


def probe(url):
    request = Request(url, headers={"User-Agent": "MTDT-catalog-preflight/1.0"})
    try:
        with urlopen(request, timeout=15) as response:
            result = {"url": url, "status": response.status, "final_url": response.url}
            content_type = response.headers.get("content-type", "")
            if "json" in content_type:
                value = json.loads(response.read(1024 * 1024))
                fields = ("issuer", "resource", "authorization_servers", "authorization_endpoint", "token_endpoint", "registration_endpoint", "userinfo_endpoint", "authorization_response_iss_parameter_supported", "scopes_supported", "code_challenge_methods_supported")
                result["metadata"] = {key: value[key] for key in fields if key in value}
            return result
    except HTTPError as error:
        return {"url": url, "status": error.code, "www_authenticate": error.headers.get("www-authenticate", "")}
    except (URLError, TimeoutError, ValueError) as error:
        return {"url": url, "status": None, "error": str(error)}


def preflight(args):
    manifest = openai_manifest()
    interface = manifest["interface"]
    connector = read_json(ROOT / "publishing/claude-connector.json")
    urls = list(dict.fromkeys([interface[k] for k in ("websiteURL", "supportURL", "privacyPolicyURL", "termsOfServiceURL")] + [connector["listing"]["documentation_url"], ENDPOINT, connector["authentication"]["protected_resource_metadata_url"], connector["authentication"]["issuer"] + "/.well-known/openid-configuration"]))
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(probe, urls))
    issues = []
    for result in results:
        expected = 401 if result["url"] == ENDPOINT else 200
        if result["status"] != expected:
            issues.append(f"Unexpected public HTTP response: {result['url']} -> {result['status']}")
        if result["url"] == ENDPOINT and "resource_metadata=" not in result.get("www_authenticate", ""):
            issues.append("MCP 401 is missing the resource metadata challenge")
    by_url = {r["url"]: r for r in results}
    auth = by_url[connector["authentication"]["issuer"] + "/.well-known/openid-configuration"].get("metadata", {})
    if not auth.get("registration_endpoint") or "S256" not in auth.get("code_challenge_methods_supported", []):
        issues.append("OAuth metadata does not advertise DCR and S256 PKCE")
    if not auth.get("userinfo_endpoint") or not {"openid", "email"} <= set(auth.get("scopes_supported", [])):
        issues.append("Verify OIDC UserInfo and openid/email support for OpenAI workspace domain restrictions")
    prm = by_url[connector["authentication"]["protected_resource_metadata_url"]].get("metadata", {})
    if connector["authentication"]["issuer"] not in prm.get("authorization_servers", []):
        issues.append("Unexpected protected-resource authorization server")
    if not {"mtdt:read", "mtdt:deploy"} <= set(prm.get("scopes_supported", [])):
        issues.append("Protected-resource metadata is missing the MTDT scopes")
    evidence, tools = inventory(args.tools_json or ROOT / "publishing/tool-inventory.json")
    annotation_gaps = [t["name"] for t in tools if not t.get("annotations", {}).get("readOnlyHint") and not t.get("annotations", {}).get("destructiveHint")]
    missing_titles = [t["name"] for t in tools if not (t.get("title") or t.get("annotations", {}).get("title"))]
    if not tools:
        issues.append("No tools in the inspected inventory")
    if annotation_gaps:
        issues.append("Resolve Claude write-annotation compatibility (#1324)")
    if missing_titles:
        issues.append("Tools missing display titles")
    if not (ROOT / "LICENSE").exists() and not read_json(ROOT / ".claude-plugin/plugin.json").get("license"):
        issues.append("Owner must select a license for the Claude plugin bundle")
    if evidence.get("live") is not True:
        issues.append("Collect and compare a fresh live tools/list; local inventory is not live evidence")
    issues.extend([
        "Prepare and privately supply dedicated reviewer account and isolated fixture team",
        "Run the 5 positive and 3 negative cases as reviewer and record their evidence",
        "Verify reviewer OAuth login, refresh and verified email/UserInfo through the actual clients",
        "Exercise all exposed tools in Claude before the testing attestation",
        "Supply a reviewer-accessible real demo recording URL for OpenAI",
        "Complete portal identity/ownership verification, scans and owner policy attestations",
    ])
    report = {"observed_at": datetime.now(timezone.utc).isoformat(), "public_probes": results, "tool_inventory_evidence": evidence, "tool_count": len(tools), "missing_titles": missing_titles, "claude_write_annotation_gaps": annotation_gaps, "submission_prerequisites": issues, "ready_to_submit": not issues, "scope": "Unauthenticated public discovery plus supplied inventory; no OAuth login, runtime tool call or portal submission"}
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(json_bytes(report))
        print(f"Wrote {path}")
    else:
        print(json_bytes(report).decode("utf-8"))
    print(f"Public probes: {len(results)}; tools: {len(tools)}; Claude annotation gaps: {len(annotation_gaps)}")
    if args.require_ready and issues:
        return 2
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("build", help="Build both minimal distribution ZIPs")
    command.add_argument("--demo-url")
    commands.add_parser("check", help="Check source metadata and generated ZIPs")
    command = commands.add_parser("preflight", help="Probe public URLs and inspect a tool inventory")
    command.add_argument("--tools-json", type=Path)
    command.add_argument("--output", type=Path)
    command.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "build":
            build(args)
        elif args.command == "check":
            check(args)
        else:
            return preflight(args)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print(f"Publication check failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
