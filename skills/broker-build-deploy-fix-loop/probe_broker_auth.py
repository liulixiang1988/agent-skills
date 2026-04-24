"""Authenticated broker probe — mint x5c+token from Key Vault and hit the dev App Service.

Used by the broker-build-deploy-fix-loop skill as the final validation step.

Target paths:
  /                — goes through YARP; RequestTransformer uses the full URI
                     from x-ms-lumina-sandbox-target-uri as the upstream URL.
                     Exercises full auth handler + proxy pipeline.
  /healthz/ready   — bypasses auth (registered before UseRouting). Only useful
                     as a liveness probe, not an auth check.

Prereqs:
  - `az login` with access to Key Vault `lumina-dev` (subscription
    e75c95f3-27b4-410f-a40e-2b9153a807dd, resource group browser-tools).
  - Python `cryptography` package (anaconda default env has it).

Checks:
  1. liveness                      /healthz/ready                      → 200 Healthy
  2. bing upstream (happy path)    target-uri=https://www.bing.com/    → 200 (bing HTML)
  3. cache hit (same kid, no x5c)  target-uri=https://www.bing.com/    → 200
  4. orchestrator upstream         target-uri=https://luminasandbox…   → non-401 (RBAC denied from orch, e.g. 403)
  5. missing token                 target-uri=https://www.bing.com/    → 401 (broker auth)
  6. wrong audience                                                    → 401
  7. wrong issuer                                                      → 401

HTTP 502 means port 8080 isn't reachable (container crash loop); check
`az webapp log tail` instead of trying to diagnose auth.
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
BROKER = "lumina-sandbox-broker-dev-westus2.azurewebsites.net"
LIVENESS_URL = f"https://{BROKER}/healthz/ready"
PROXY_ROOT_URL = f"https://{BROKER}/"
ORCH_HOST = "luminasandboxorchestrator-g-2.luminadevaksprovider-westus2.dev.copilotlumina.com"
ORCH_URL = f"https://{BROKER}/sandbox-orchestrator"
ISSUER = "Lumina"
AUDIENCE = "SandboxBroker"

TARGET_URI_HEADER = "x-ms-lumina-sandbox-target-uri"
TOKEN_HEADER = "x-ms-lumina-sandbox-broker-token"
X5C_HEADER = "x-ms-lumina-sandbox-broker-token-x5c"


def download_pfx() -> bytes:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pfx") as f:
        pfx_path = Path(f.name)
    pfx_path.unlink(missing_ok=True)
    subprocess.run(
        ["az", "keyvault", "secret", "download", "--vault-name", VAULT,
         "--name", SECRET, "--encoding", "base64", "--file", str(pfx_path)],
        check=True,
        shell=(sys.platform == "win32"),
    )
    data = pfx_path.read_bytes()
    pfx_path.unlink(missing_ok=True)
    return data


def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def load_chain(pfx: bytes):
    key, leaf, intermediates = pkcs12.load_key_and_certificates(pfx, password=None)
    chain = [leaf] + list(intermediates or [])
    thumbprint = hashlib.sha1(leaf.public_bytes(serialization.Encoding.DER)).hexdigest().upper()
    x5c = ";".join(
        base64.b64encode(c.public_bytes(serialization.Encoding.DER)).decode()
        for c in chain
    )
    return key, chain, thumbprint, x5c


def mint_token(key, thumbprint: str, *, issuer: str = ISSUER, audience: str = AUDIENCE,
               exp_offset: int = 600) -> str:
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT", "kid": thumbprint}
    claims = {
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "nbf": now - 30,
        "exp": now + exp_offset,
        "sub": "broker-loop-probe",
    }
    signing_input = (
        b64url(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + b64url(json.dumps(claims, separators=(",", ":")).encode())
    )
    sig = key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    return signing_input + "." + b64url(sig)


def call(url: str, target_uri: str | None, *, token: str | None = None,
         x5c: str | None = None) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET")
    if target_uri is not None:
        req.add_header(TARGET_URI_HEADER, target_uri)
    if token is not None:
        req.add_header(TOKEN_HEADER, token)
    if x5c is not None:
        req.add_header(X5C_HEADER, x5c)
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=30) as resp:
            return resp.status, resp.read()[:500].decode(errors="replace")
    except urllib.error.HTTPError as e:
        try:
            body = e.read()[:500].decode(errors="replace")
        except Exception:
            body = ""
        return e.code, body


def check(label: str, predicate, code: int, body: str) -> bool:
    ok = predicate(code)
    marker = "OK" if ok else "FAIL"
    print(f"[{marker}] {label}: got {code}")
    if not ok:
        print(f"       body: {body[:200]}")
    return ok


def eq(n: int):
    return lambda c: c == n


def main() -> int:
    pfx = download_pfx()
    key, _chain, thumbprint, x5c = load_chain(pfx)
    print(f"[info] kid (leaf SHA1 thumbprint) = {thumbprint}")

    results = []

    # 1) Liveness (auth-bypassed)
    code, body = call(LIVENESS_URL, None)
    results.append(check("liveness /healthz/ready", eq(200), code, body))

    # 2) Bing upstream — happy path through auth + YARP
    token = mint_token(key, thumbprint)
    code, body = call(PROXY_ROOT_URL, "https://www.bing.com/", token=token, x5c=x5c)
    results.append(check("bing upstream (auth+proxy)", eq(200), code, body))

    # 3) Cache hit: same kid, omit x5c
    token2 = mint_token(key, thumbprint)
    code, body = call(PROXY_ROOT_URL, "https://www.bing.com/", token=token2)
    results.append(check("cache hit (same kid, no x5c)", eq(200), code, body))

    # 4) Orchestrator upstream — auth passes broker, orch returns RBAC denied
    token3 = mint_token(key, thumbprint)
    orch_target_uri = f"https://{ORCH_HOST}/sandbox-orchestrator"
    code, body = call(PROXY_ROOT_URL, orch_target_uri, token=token3, x5c=x5c)
    def orch_ok(c):
        if c == 401 and "rbac" in body.lower():
            return True
        return c != 401
    results.append(check("orchestrator upstream (RBAC expected)", orch_ok, code, body))

    # 5) Missing token → 401 from broker
    code, body = call(PROXY_ROOT_URL, "https://www.bing.com/")
    results.append(check("missing token", eq(401), code, body))

    # 6) Wrong audience → 401
    bad_aud = mint_token(key, thumbprint, audience="WrongAudience")
    code, body = call(PROXY_ROOT_URL, "https://www.bing.com/", token=bad_aud, x5c=x5c)
    results.append(check("wrong audience", eq(401), code, body))

    # 7) Wrong issuer → 401
    bad_iss = mint_token(key, thumbprint, issuer="WrongIssuer")
    code, body = call(PROXY_ROOT_URL, "https://www.bing.com/", token=bad_iss, x5c=x5c)
    results.append(check("wrong issuer", eq(401), code, body))

    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
