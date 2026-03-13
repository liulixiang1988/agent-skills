---
name: kv-cert
description: "Azure Key Vault certificate management. TRIGGER when: user asks to create/view/manage SSL certificates in Azure Key Vault, import certificates to App Service, bind custom domains with SSL, grant KV RBAC permissions, or troubleshoot KV certificate issues (e.g., 'create KV cert', 'add SSL to app service', 'bind custom domain', 'grant KV permission', 'KV 证书', '创建证书', '绑定域名', 'SSL 绑定')."
---

# Azure Key Vault Certificate Management

Manage SSL certificates in Azure Key Vault and bind them to App Service custom domains.

## RBAC Permissions

KV uses RBAC authorization. Key roles:

| Role | Purpose | Role Definition ID |
|---|---|---|
| Key Vault Certificate User | Read certs | `db79e9a7-68ee-4b58-9aeb-b90e7c24fcba` |
| Key Vault Certificates Officer | Create/import/delete certs | `a4417e6f-fecd-4de8-b567-7b0420556985` |
| Key Vault Secrets User | Read secrets (cert private keys are stored as secrets) | `4633458b-17de-408a-b874-0445c86b69e6` |

### Grant RBAC via REST API

`az role assignment create` may fail with `MissingSubscription` in some CLI versions. Use REST API instead:

```bash
# Get current user Object ID
user_oid=$(az ad signed-in-user show --query id -o tsv)

# Get KV resource ID
kv_id=$(az keyvault show --name <kv-name> --resource-group <rg> --query id -o tsv)

# Grant Key Vault Certificates Officer
az rest --method PUT \
  --url "https://management.azure.com${kv_id}/providers/Microsoft.Authorization/roleAssignments/$(python -c 'import uuid; print(uuid.uuid4())')?api-version=2022-04-01" \
  --body "{
    \"properties\": {
      \"roleDefinitionId\": \"/subscriptions/<sub-id>/providers/Microsoft.Authorization/roleDefinitions/a4417e6f-fecd-4de8-b567-7b0420556985\",
      \"principalId\": \"${user_oid}\",
      \"principalType\": \"User\"
    }
  }"
```

> RBAC propagation takes 1-5 minutes.

### Grant App Service WebApp SP access to KV

App Service reads KV certs via the **Azure WebApp 1st-party Service Principal** (Application ID: `abfa0a7c-a6b6-4736-8310-5855508787cd`, Display Name: `Microsoft Azure App Service`), NOT the UAMI bound to the App Service.

> **CRITICAL: Application ID ≠ Object ID.** RBAC `principalId` must use Object ID, not Application ID. Using Application ID silently assigns to the wrong principal.

Grant it `Key Vault Certificate User` + `Key Vault Secrets User` roles:

```bash
azure_webapp_app_id="abfa0a7c-a6b6-4736-8310-5855508787cd"
# Resolve Object ID (different per tenant — never hardcode)
azure_webapp_sp_oid=$(az ad sp show --id "${azure_webapp_app_id}" --query id -o tsv)
# Use the REST API pattern above with principalId="${azure_webapp_sp_oid}" and principalType ServicePrincipal
# Roles needed: db79e9a7-... (Certificate User) + 4633458b-... (Secrets User)
```

## Common Queries

```bash
# List certificates in KV
az keyvault certificate list --vault-name <kv-name> \
  --query "[].{name:name, thumbprint:x509ThumbprintHex}" -o table

# Show certificate details
az keyvault certificate show --vault-name <kv-name> --name <cert-name> \
  --query "{
    name:name, thumbprint:x509ThumbprintHex,
    subject:policy.x509CertificateProperties.subject,
    notBefore:attributes.notBefore, expires:attributes.expires,
    issuer:policy.issuerParameters.name,
    sansCount:length(policy.x509CertificateProperties.subjectAlternativeNames.dnsNames)
  }" -o json

# Show SAN list
az keyvault certificate show --vault-name <kv-name> --name <cert-name> \
  --query "policy.x509CertificateProperties.subjectAlternativeNames.dnsNames" -o json

# List configured issuers
az keyvault certificate issuer list --vault-name <kv-name> -o table
```

## Create Certificate via OneCert CA

### 1. Prepare Policy JSON

```json
{
  "issuerParameters": { "name": "OneCertV2-PublicCA" },
  "keyProperties": { "exportable": true, "keySize": 2048, "keyType": "RSA", "reuseKey": false },
  "lifetimeActions": [{ "action": { "actionType": "AutoRenew" }, "trigger": { "lifetimePercentage": 80 } }],
  "secretProperties": { "contentType": "application/x-pkcs12" },
  "x509CertificateProperties": {
    "ekus": ["1.3.6.1.5.5.7.3.1", "1.3.6.1.5.5.7.3.2"],
    "keyUsage": ["digitalSignature", "keyEncipherment"],
    "subject": "CN=*.example.dev.copilotlumina.com",
    "subjectAlternativeNames": {
      "dnsNames": [
        "*.example.dev.copilotlumina.com",
        "*.sub1.example.dev.copilotlumina.com"
      ]
    },
    "validityInMonths": 6
  }
}
```

**Key fields:**
- `issuerParameters.name` — must be a CA configured in the KV (`az keyvault certificate issuer list`)
- `subject` — Certificate CN; also add it to SAN dnsNames (modern clients only check SAN)
- `lifetimeActions.AutoRenew` — auto-renew at 80% lifetime
- `ekus` — `1.3.6.1.5.5.7.3.1` = Server Auth, `1.3.6.1.5.5.7.3.2` = Client Auth
- `contentType` — `application/x-pkcs12` = PFX format with private key

### 2. Create

```bash
az keyvault certificate create \
  --vault-name <kv-name> --name <cert-name> \
  --policy @cert-policy.json
```

### 3. Copy policy from existing cert

```bash
# Export policy
az keyvault certificate show --vault-name <source-kv> --name <source-cert> \
  --query "policy" -o json > cert-policy.json
# Edit: change subject/CN, dnsNames, remove read-only fields (attributes, id)
# Create with new policy
az keyvault certificate create --vault-name <target-kv> --name <new-cert> --policy @cert-policy.json
```

## App Service: Import KV Certificate & Bind Custom Domains

### Step 1: Import certificate

```bash
thumbprint=$(az webapp config ssl import \
  --name <webapp-name> --resource-group <rg> \
  --key-vault <kv-name> --key-vault-certificate-name <cert-name> \
  --query thumbprint -o tsv)
```

### Step 2: Add custom hostname

```bash
az webapp config hostname add \
  --webapp-name <webapp-name> --resource-group <rg> \
  --hostname "*.example.dev.copilotlumina.com"
```

> Prerequisite: DNS CNAME to `<webapp>.azurewebsites.net`, or TXT record `asuid.<hostname>` for domain verification.

### Step 3: Bind SSL (SNI)

```bash
az webapp config ssl bind \
  --name <webapp-name> --resource-group <rg> \
  --certificate-thumbprint <thumbprint> --ssl-type SNI
```

### Batch operation pattern

```bash
thumbprint=$(az webapp config ssl import --name ${webapp} --resource-group ${rg} \
  --key-vault ${kv} --key-vault-certificate-name ${cert} --query thumbprint -o tsv)

for hostname in "${hostnames[@]}"; do
  az webapp config hostname add --webapp-name ${webapp} --resource-group ${rg} \
    --hostname "${hostname}" 2>/dev/null || true
  az webapp config ssl bind --name ${webapp} --resource-group ${rg} \
    --certificate-thumbprint ${thumbprint} --ssl-type SNI 2>/dev/null || true
done
```

## Verify App Service Bindings

```bash
# List custom hostnames
az webapp config hostname list --webapp-name <webapp> --resource-group <rg> -o table

# List SSL certificates
az webapp config ssl list --resource-group <rg> \
  --query "[].{name:name, thumbprint:thumbprint, subject:subjectName, expires:expirationDate}" -o table

# Show hostname + SSL binding status
az webapp show --name <webapp> --resource-group <rg> \
  --query "hostNameSslStates[].{name:name, sslState:sslState, thumbprint:thumbprint}" -o table
```

## Common Issues

| Problem | Solution |
|---|---|
| `az role assignment create` → `MissingSubscription` | Use `az rest --method PUT` REST API instead |
| `ForbiddenByConnection` | KV has public network access disabled — enable temporarily or use Private Endpoint/VPN |
| `ForbiddenByRbac` | Missing RBAC role — grant via REST API (see above) |
| CN not in SAN → domain invalid | Always include CN in SAN dnsNames; modern clients only check SAN |
| App Service can't read KV cert | Grant `Key Vault Certificate User` + `Key Vault Secrets User` to WebApp 1st-party SP. Use **Object ID** (via `az ad sp show --id "abfa0a7c-..." --query id`), NOT Application ID |

## Network Access

If KV has public network access disabled (`ForbiddenByConnection`):
- Temporarily enable public access (Portal → KV → Networking)
- Or use Private Endpoint / VPN
- AKS pods cannot reach KV private endpoint unless a Private DNS Zone for `privatelink.vaultcore.azure.net` is linked to the AKS VNet
