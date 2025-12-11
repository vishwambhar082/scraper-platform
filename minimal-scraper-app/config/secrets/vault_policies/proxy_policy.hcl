# Policy: access to proxy configuration for scraper platform

path "secret/data/scraper/shared/proxies" {
  capabilities = ["read"]
}

path "secret/metadata/scraper/shared/proxies" {
  capabilities = ["read"]
}
