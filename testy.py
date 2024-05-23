import tomllib

import requests

with open("config.toml", "rb") as f:
    config = tomllib.load(f)

APIKEY = config["apikey"]

QUERY = """
query getEventId($slug: String) {
  event(slug: $slug) {
    id
    name
  }
}
"""
VARIABLES = {"slug": "tournament/the-nightclub-s9e15-os-nyc/event/melee-singles"}

while True:
    resp = requests.post(
        "https://api.smash.gg/gql/alpha",
        json={"query": QUERY, "variables": VARIABLES},
        headers={"Authorization": f"Bearer {APIKEY}"},
        timeout=30,
    )
    print(resp.status_code)
    print(resp.headers)
    print(resp.text)
