# Policy: access to proxy configuration and credentials
# This is an alias for proxy_policy.hcl to match v5.0 spec naming

path "secret/data/scraper/shared/proxies" {
  capabilities = ["read"]
}

path "secret/metadata/scraper/shared/proxies" {
  capabilities = ["read"]
}

path "secret/data/scraper/proxies/*" {
  capabilities = ["read"]
}

path "secret/metadata/scraper/proxies/*" {
  capabilities = ["read"]
}

