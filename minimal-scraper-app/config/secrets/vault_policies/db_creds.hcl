# Policy: access to database credentials for scraper-platform

path "secret/data/scraper/database/credentials" {
  capabilities = ["read"]
}

path "secret/metadata/scraper/database/credentials" {
  capabilities = ["read"]
}

path "secret/data/scraper/database/readonly" {
  capabilities = ["read"]
}

path "secret/metadata/scraper/database/readonly" {
  capabilities = ["read"]
}

