# Policy: access to account credentials for each source

path "secret/data/scraper/alfabeta/accounts" {
  capabilities = ["read"]
}

path "secret/data/scraper/quebec/accounts" {
  capabilities = ["read"]
}

path "secret/data/scraper/lafa/accounts" {
  capabilities = ["read"]
}

path "secret/metadata/scraper/*/accounts" {
  capabilities = ["read"]
}
