# General policy for scraper-platform-v4.8 service

path "sys/health" {
  capabilities = ["read"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}

path "secret/data/scraper/config/*" {
  capabilities = ["read"]
}

path "secret/metadata/scraper/config/*" {
  capabilities = ["read"]
}
