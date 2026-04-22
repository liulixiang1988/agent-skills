"""Extended auth matrix for the Lumina broker dev deployment.

Imports helpers from the probe skill but adds more scenarios:
  headers-only negatives, expired/future tokens, tampered signature,
  unknown kid, HTTP POST, and baseline happy path.
"""
import importlib.util
import pathlib
import sys
import time
import base64
import json

SKILL = pathlib.Path.home() / ".claude/skills/broker-build-deploy-fix-loop/probe_broker_auth.py"
spec = importlib.util.spec_from_file_location("probe", SKILL)
probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)

BROKER_ROOT = probe.PROXY_ROOT_URL
BING = "www.bing.com"

pfx = probe.download_pfx()
key, chain, thumbprint, x5c = probe.load_chain(pfx)
print(f"[info] leaf kid = {thumbprint}\n")

results = []
def run(label, code_expected, *, target=BING, token="__default__", x5c_header="__default__", url=BROKER_ROOT):
    if token == "__default__":
        token = probe.mint_token(key, thumbprint)
    if x5c_header == "__default__":
        x5c_header = x5c
    code, body = probe.call(url, target, token=token, x5c=x5c_header)
    ok = code == code_expected if isinstance(code_expected, int) else code_expected(code)
    marker = "PASS" if ok else "FAIL"
    snippet = body.strip().splitlines()[0][:80] if body else ""
    results.append((label, code, marker, snippet))
    print(f"  [{marker}] {label:50s} got={code}  expected={code_expected}")

print("=== Happy path ===")
run("baseline: valid token + x5c -> proxy 200", 200)
run("liveness /healthz/ready (no headers)", 200, target=None, token=None, x5c_header=None,
    url=probe.LIVENESS_URL)

print("\n=== Missing headers ===")
run("no token, no x5c", 401, token=None, x5c_header=None)
run("no token, x5c present", 401, token=None)
run("token present, no x5c (cold cache expected)", lambda c: c in (200, 401))
run("no target-host header", lambda c: c in (400, 401, 404, 502),
    target=None)

print("\n=== Token claim mismatches ===")
run("wrong audience", 401, token=probe.mint_token(key, thumbprint, audience="WrongAud"))
run("wrong issuer",   401, token=probe.mint_token(key, thumbprint, issuer="WrongIss"))
run("expired token (exp in past)", 401,
    token=probe.mint_token(key, thumbprint, exp_offset=-60))

# not-yet-valid: mint with nbf manually (we only have exp_offset; build by hand)
now = int(time.time())
hdr = {"alg": "RS256", "typ": "JWT", "kid": thumbprint}
future_claims = {"iss": probe.ISSUER, "aud": probe.AUDIENCE,
                 "iat": now + 3600, "nbf": now + 3600, "exp": now + 7200,
                 "sub": "probe"}
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
signing_input = (probe.b64url(json.dumps(hdr, separators=(",", ":")).encode()) + "."
                 + probe.b64url(json.dumps(future_claims, separators=(",", ":")).encode()))
sig = key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
future_token = signing_input + "." + probe.b64url(sig)
run("not-yet-valid token (nbf in future)", 401, token=future_token)

print("\n=== Signature / kid tampering ===")
good = probe.mint_token(key, thumbprint)
parts = good.split(".")
tampered_sig = parts[0] + "." + parts[1] + "." + probe.b64url(b"\x00" * 256)
run("tampered signature", 401, token=tampered_sig)

# Flip one byte of the payload (claims) — signature will no longer match
claims_bytes = base64.urlsafe_b64decode(parts[1] + "==")
claims_obj = json.loads(claims_bytes)
claims_obj["sub"] = "tampered"
new_claims_b64 = probe.b64url(json.dumps(claims_obj, separators=(",", ":")).encode())
tampered_claims = parts[0] + "." + new_claims_b64 + "." + parts[2]
run("tampered claims (sig no longer matches)", 401, token=tampered_claims)

unknown_kid = "0" * 40
run("unknown kid in header, no x5c", 401,
    token=probe.mint_token(key, unknown_kid), x5c_header=None)

print("\n=== Path / proxy variants ===")
run("orchestrator upstream (broker auth OK, RBAC at orch)",
    lambda c: c != 401 or "rbac" in (results[-1] if False else "").lower() or c == 403,
    target=probe.ORCH_HOST, url=probe.ORCH_URL)

print("\n=== Summary ===")
for label, code, marker, snippet in results:
    print(f"  {marker:4s} | HTTP {code:3d} | {label}  {('— ' + snippet) if snippet else ''}")
passed = sum(1 for r in results if r[2] == "PASS")
print(f"\n{passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
