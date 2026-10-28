import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def docker(*arguments):
    return subprocess.check_output(["docker", *arguments], cwd=ROOT, text=True).strip()


def request(path, payload=None, expected=200):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        "http://localhost" + path,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        response = urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        assert response.status == expected, f"{path}: HTTP {response.status}, expected {expected}"
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--recreate", action="store_true", help="Recreate this project's containers")
    args = parser.parse_args()

    assert request("/health") == {"status": "ok"}
    print("PASS: /health returns HTTP 200 through Nginx", flush=True)
    request("/notes", {"text": "   "}, expected=422)
    request("/notes", {"text": "x" * 1001}, expected=422)
    marker = "persistence-" + uuid.uuid4().hex
    note = request("/notes", {"text": marker}, expected=201)
    assert note["text"] == marker
    assert any(item["id"] == note["id"] for item in request("/notes"))
    print("PASS: note creation, reading and input validation", flush=True)
    print(f"Created note #{note['id']}: {marker}", flush=True)

    for service in ("nginx", "app", "db"):
        container_id = docker("compose", "ps", "-q", service)
        assert container_id, f"{service}: container missing"
        container = json.loads(docker("inspect", container_id))[0]
        assert container["State"]["Health"]["Status"] == "healthy", f"{service}: unhealthy"
        bindings = container["HostConfig"]["PortBindings"] or {}
        if service == "nginx":
            assert set(bindings) == {"80/tcp"}
            assert all(binding["HostPort"] == "80" for binding in bindings["80/tcp"])
        else:
            assert not bindings, f"{service}: unexpected published ports"
        expected_networks = {
            "nginx": {"mipt-prac2_frontend"},
            "app": {"mipt-prac2_frontend", "mipt-prac2_backend"},
            "db": {"mipt-prac2_backend"},
        }
        assert set(container["NetworkSettings"]["Networks"]) == expected_networks[service]
        if service == "app":
            uid = docker("compose", "exec", "-T", "app", "id", "-u")
            assert uid == "10001", f"app: unexpected UID {uid}"
    backend = json.loads(docker("network", "inspect", "mipt-prac2_backend"))[0]
    assert backend["Internal"], "backend: network must be internal"
    print("PASS: all services healthy; only Nginx:80 published; app UID=10001", flush=True)
    print("PASS: frontend/backend separation; backend is internal", flush=True)

    if args.recreate:
        old_db = docker("compose", "ps", "-q", "db")
        print("Recreating Compose containers without removing pgdata...", flush=True)
        result = subprocess.run(
            ["docker", "compose", "up", "-d", "--force-recreate", "--wait", "--wait-timeout", "120"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            print(result.stdout + result.stderr, file=sys.stderr)
            result.check_returncode()
        assert docker("compose", "ps", "-q", "db") != old_db
        assert request("/health") == {"status": "ok"}
        assert any(item["id"] == note["id"] and item["text"] == marker for item in request("/notes"))
        print("PASS: PostgreSQL note survived container recreation", flush=True)
        print(f"Found note #{note['id']} after recreation: {marker}", flush=True)


if __name__ == "__main__":
    main()
