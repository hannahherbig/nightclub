import trueskill
from collections import defaultdict
import json
import pathlib
from tabulate import tabulate
from datetime import datetime

data = json.loads(pathlib.Path("onlynoobs.json").read_text())


class Player:
    prefix = None
    tag = None
    sets = 0
    wins = 0
    rating = trueskill.Rating()


players = defaultdict(Player)


def get_players(players_l):
    d = {}
    for player_d in players_l:
        player_d = player_d["player"]
        player = players[player_d["id"]]
        player.tag = player_d["gamerTag"]
        d[player_d["id"]] = player
    return d


for set in sorted(
    [set for set in data["sets"].values() if set["completedAt"] is not None],
    key=lambda set: set["completedAt"],
):
    print(json.dumps(set))
    slot1, slot2 = set["slots"]
    rating_groups = []
    scores = []
    ended = datetime.fromtimestamp(set["completedAt"])
    if ended.year != datetime.now().year:
        continue
    winners = {}
    for slot in set["slots"]:
        standing = slot["standing"]
        if standing is None:
            break
        entrant = standing["entrant"]
        players_map = {}
        ratings = {}
        for participant in entrant["participants"]:
            p = participant["player"]
            id = p["id"]
            player = players[id]
            player.prefix = p["prefix"]
            player.tag = p["gamerTag"]
            players_map[id] = player
            ratings[id] = player.rating
        if len(players_map) == 1:
            player.name = entrant["name"]
        score = standing["stats"]["score"]["value"]
        rating_groups.append(ratings)
        scores.append(score)
        if set["winnerId"] == entrant["id"]:
            winners = players_map
    if rating_groups and scores and None not in scores and -1 not in scores:
        ranks = [-x for x in scores]
        rating_groups = trueskill.rate(rating_groups, ranks)
        for g in rating_groups:
            for id, rating in g.items():
                p = players[id]
                p.rating = rating
                p.sets += 1
                if id in winners:
                    p.wins += 1

table = []
for id, player in players.items():
    if player.sets:
        table.append(
            {
                "id": id,
                "prefix": player.prefix,
                "tag": player.tag,
                "mu": player.rating.mu,
                "sigma": player.rating.sigma,
                "expose": trueskill.expose(player.rating),
                "wins": player.wins,
                "sets": player.sets,
                "win rate": player.wins / player.sets,
            }
        )
table.sort(key=lambda d: d["expose"])

print(tabulate(table, headers="keys", colalign=("right", "right")))
