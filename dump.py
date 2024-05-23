import json
import pathlib
import tomllib

import requests
from backoff import expo, on_exception
from ratelimit import RateLimitException, limits

with open("config.toml", "rb") as f:
    config = tomllib.load(f)

APIKEY = config["apikey"]

QUERY_EVENT_SETS = """
query EventSets($eventId: ID!, $page: Int!, $perPage: Int!) {
  event(id: $eventId) {
    id
    name
    sets(page: $page, perPage: $perPage, sortType: RECENT) {
      pageInfo {
        total
      }
      nodes {
        id
        completedAt
        winnerId
        state
        event { id }
        slots {
          id
          standing {
            entrant {
              id
              name
              participants {
                player {
                  id
                  prefix
                  gamerTag
                }
              }
            }
            stats {
              score {
                value
              }
            }
          }
        }
      }
    }
  }
}
"""

QUERY_TOURNAMENTS = """
query TournamentsSearch($perPage: Int, $page: Int, $coordinates: String!, $radius: String!, $game: ID!, $name: String!) {
  tournaments(
    query: {perPage: $perPage, filter: {location: {distanceFrom: $coordinates, distance: $radius}, videogameIds: [$game], name: $name}, page: $page}
  ) {
    pageInfo {
      total
    }
    nodes {
      id
      name
      city
      slug
      addrState
      endAt
      events {
        id
        name
        slug
        videogame {
          id
        }
        sets(page: 1, perPage: 1) {
          pageInfo {
            total
          }
        }
      }
    }
  }
}
"""

QUERY_TOURNAMENTS_OWNER = """
query TournamentsSearch($perPage: Int, $page: Int, $game: ID!, $ownerId: ID!) {
  tournaments(
    query: {perPage: $perPage, filter: {videogameIds: [$game], ownerId: $ownerId}, page: $page}
  ) {
    pageInfo {
      total
    }
    nodes {
      id
      name
      city
      slug
      addrState
      endAt
      events {
        id
        name
        slug
        videogame {
          id
        }
        sets(page: 1, perPage: 1) {
          pageInfo {
            total
          }
        }
      }
    }
  }
}
"""


def on_backoff(d):
    del d["target"]
    del d["args"]
    del d["kwargs"]
    print("backoff", d)


@on_exception(
    expo,
    (
        RateLimitException,
        requests.HTTPError,
        requests.Timeout,
        requests.JSONDecodeError,
    ),
    on_backoff=on_backoff,
)
@limits(calls=80, period=60)
def query(query, variables):
    resp = requests.post(
        "https://api.smash.gg/gql/alpha",
        json={"query": query, "variables": variables},
        headers={"Authorization": f"Bearer {apikey}"},
        timeout=30,
    )
    print(resp.text)
    resp.raise_for_status()
    return resp.json()


def fetch_sets(event):
    page = 1
    count = 0
    while True:
        result = query(
            QUERY_EVENT_SETS, {"eventId": event, "page": page, "perPage": 32}
        )
        result = result["data"]["event"]["sets"]
        yield from result["nodes"]
        count += len(result["nodes"])
        if count >= result["pageInfo"]["total"]:
            break
        page += 1


def find_nightclubs():
    page = 1
    count = 0
    while True:
        result = query(
            QUERY_TOURNAMENTS,
            {
                "perPage": 200,
                "page": page,
                "coordinates": "40.7159481,-73.9994085",
                "radius": "1mi",
                "game": 1,
                "name": "nightclub",
            },
        )
        result = result["data"]["tournaments"]
        yield from result["nodes"]
        count += len(result["nodes"])
        if count >= result["pageInfo"]["total"]:
            break
        page += 1


def find_onlynoobs():
    page = 1
    count = 0
    while True:
        result = query(
            QUERY_TOURNAMENTS_OWNER,
            {
                "perPage": 200,
                "page": page,
                "game": 1,
                "ownerId": 507353,
            },
        )
        result = result["data"]["tournaments"]
        yield from result["nodes"]
        count += len(result["nodes"])
        if count >= result["pageInfo"]["total"]:
            break
        page += 1


event_whitelist = {
    # "Crew Battle (2 Teams)",
    # "Low Tier Singles",
    # "Melee Doubles",
    "Melee Ladder",
    "Melee Singles",
    "Redemption Bracket",
    "Redemption Bracket (0-2/1-2/2-2ers)",
    "Redemption Bracket (Only happens if less than 64 entrants)",
    # "Spectator Pass",
    # "Spectators Only",
    # "The Waitlist",
}
event_names = set()

sets = {}
tourneys = {}
for tourney in find_nightclubs():
    tourneys[tourney["id"]] = tourney
    for event in tourney["events"]:
        event_names.add(event["name"])
        if event["name"] in event_whitelist:
            print(json.dumps(event))
            for set in fetch_sets(event["id"]):
                sets[set["id"]] = set

print(sorted(event_names))
pathlib.Path("onlynoobs.json").write_text(
    json.dumps({"tourneys": tourneys, "sets": sets}, indent=2)
)
