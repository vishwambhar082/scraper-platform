# Policy: access to scraper API tokens and authentication credentials

path "secret/data/scraper/tokens/api" {
  capabilities = ["read"]
}

path "secret/data/scraper/tokens/oauth" {
  capabilities = ["read"]
}

path "secret/data/scraper/tokens/service_accounts" {
  capabilities = ["read"]
}

path "secret/metadata/scraper/tokens/*" {
  capabilities = ["read"]
}

