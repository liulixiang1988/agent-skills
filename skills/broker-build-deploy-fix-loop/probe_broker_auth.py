"""Authenticated broker probe — mint x5c+token from Key Vault and hit the dev App Service.

Used by the broker-build-deploy-fix-loop skill as the final validation step.

Prereqs:
  - `az login` with access to Key Vault `lumina-dev` (subscription
    e75c95f3-27b4-410f-a40e-2b9153a807dd, resource group browser-tools).
  - Python packages `cryptography` and `jwt` (anaconda default env has these).

A successful run prints `HTTP 200 Healthy`. Any HTTP 4xx means the broker
rejected auth — the cert chain / token claims / subject allowlist need
investigation. HTTP 502 means port 8080 isn't reachable (container crash
loop, Kestrel not bound); check `az webapp log tail` instead.
"""
import base64
import hashlib
import json
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12

VAULT = "lumina-dev"
SECRET = "SelfSignedToken"
TARGET = "lumina-sandbox-broker-dev-westus2.azurewebsites.net"
URL = f"https://{TARGET}/healthz/ready"
ISSUER = "Lumina"
AUDIENCE = "SandboxService"


def download_pfx() -> bytes:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pfx") as f:
        pfx_path = Path(f.name)
    subprocess.run(
        ["az", "keyvault", "secret", "download", "--vault-name", VAULT,
         "--name", SECRET, "--encoding", "base64", "--file", str(pfx_path)],
        check=True,
    )
    data = pfx_path.read_bytes()
    pfx_path.unlink(missing_ok=True)
    return data


def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def mint_token_and_x5c(pfx: bytes) -> tuple[str, str, str]:
    key, leaf, intermediates = pkcs12.load_key_and_certificates(pfx, password=None)
    chain = [leaf] + list(intermediates or [])
    thumbprint = hashlib.sha1(leaf.public_bytes(serialization.Encoding.DER)).hexdigest().upper()
    x5c = ";".join(
        base64.b64encode(c.public_bytes(serialization.Encoding.DER)).decode()
        for c in chain
    )
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT", "kid": thumbprint}
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "nbf": now - 30,
        "exp": now + 600,
        "sub": "broker-loop-probe",
    }
    signing_input = (
        b64url(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + b64url(json.dumps(claims, separators=(",", ":")).encode())
    )
    sig = key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    return signing_input + "." + b64url(sig), x5c, thumbprint


def probe(token: str, x5c: str) -> int:
    req = urllib.request.Request(URL, method="GET")
    req.add_header("x-ms-lumina-target-host", TARGET)
    req.add_header("x-ms-lumina-sandbox-broker-token", token)
    req.add_header("x-ms-lumina-x5c", x5c)
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=30) as resp:
            print(f"HTTP {resp.status}")
            print(resp.read()[:500].decode(errors="replace"))
            return resp.status
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}")
        try:
            print(e.read()[:500].decode(errors="replace"))
        except Exception:
            pass
        return e.code


def main() -> int:
    pfx = download_pfx()
    token, x5c, thumbprint = mint_token_and_x5c(pfx)
    print(f"[info] kid (leaf SHA1 thumbprint) = {thumbprint}")
    code = probe(token, x5c)
    return 0 if code == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
