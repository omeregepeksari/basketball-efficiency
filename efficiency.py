# GNAC men's basketball efficiency ratings
# usage: python3 efficiency.py [season ...]

import csv
import json
import re
import sys
import urllib.request
from pathlib import Path

TEAMS = {
    "Saint Martin's": "smusaints.com",
    "Alaska Anchorage": "goseawolves.com",
    "Alaska Fairbanks": "alaskananooks.com",
    "Central Washington": "wildcatsports.com",
    "Montana State Billings": "msubsports.com",
    "Northwest Nazarene": "nnusports.com",
    "Seattle Pacific": "spufalcons.com",
    "Simon Fraser": "athletics.sfu.ca",
    "Western Oregon": "wouwolves.com",
    "Western Washington": "wwuvikings.com",
}

DATA = Path(__file__).parent / "data"


def get_page(site, season):
    # cache pages so I'm not hitting every school's site each run
    path = DATA / "raw" / season / f"{site}.html"
    if not path.exists():
        url = f"https://{site}/sports/mens-basketball/stats/{season}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    return path.read_text()


def get_table(html, table_id, ncols=21):
    start = html.find(f'id="{table_id}"')
    chunk = html[start:]
    chunk = chunk[:chunk.find("</table>")]
    rows = []
    for tr in re.findall(r"<tr.*?</tr>", chunk, re.S):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)
        cells = [re.sub(r"<[^>]+>|\s+", " ", c).strip() for c in cells]
        if len(cells) == ncols:
            rows.append(cells)
    return rows


def read_box(row):
    return {
        "fga": int(row[4].split("-")[1]),
        "fta": int(row[8].split("-")[1]),
        "orb": int(row[10]),
        "tov": int(row[16]),
        "pts": int(row[19]),
    }


def possessions(box):
    return box["fga"] - box["orb"] + box["tov"] + 0.475 * box["fta"]


def ratings(us, them):
    poss = (possessions(us) + possessions(them)) / 2
    return poss, 100 * us["pts"] / poss, 100 * them["pts"] / poss


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def load_team(team, season):
    html = get_page(TEAMS[team], season)
    our_rows = get_table(html, "game-team")
    opp_rows = get_table(html, "game-opponents")

    games = []
    for us, them in zip(our_rows, opp_rows):
        if not re.match(r"\d+/\d+/\d+$", us[1]):
            continue
        poss, ortg, drtg = ratings(read_box(us), read_box(them))
        games.append({
            "date": us[1], "opponent": us[0], "result": us[3], "score": us[2],
            "poss": round(poss, 1), "ortg": round(ortg, 1), "drtg": round(drtg, 1),
            "net": round(ortg - drtg, 1), "us": read_box(us), "them": read_box(them),
        })

    # last two rows are season totals for us and opponents
    season_us = read_box(our_rows[-2])
    season_them = read_box(our_rows[-1])
    if sum(g["us"]["pts"] for g in games) != season_us["pts"]:
        raise ValueError(f"{team} {season}: game points don't add up to season total")
    if sum(g["them"]["pts"] for g in games) != season_them["pts"]:
        raise ValueError(f"{team} {season}: opponent points don't add up to season total")

    out = [{k: v for k, v in g.items() if k not in ("us", "them")} for g in games]
    write_csv(DATA / season / f"{team}.csv", out)

    poss, ortg, drtg = ratings(season_us, season_them)
    load_players(html, team, season, poss)

    conf_w, conf_l = re.search(r"Team Stats \(\d+-\d+, (\d+)-(\d+)\)", html).groups()
    wins = sum(g["result"].startswith("W") for g in games)
    return {
        "games": games,
        "record": f"{wins}-{len(games) - wins}",
        "conf": (int(conf_w), int(conf_l)),
        "pace": poss / len(games),
        "ortg": ortg,
        "drtg": drtg,
    }


def load_players(html, team, season, team_poss):
    rows = get_table(html, "individual-overall", 27)
    total = next(r for r in rows if r[1] == "Total")
    team_min = int(total[4])

    players = []
    for r in rows:
        if r[0] in ("", "TM") or r[4] == "0":
            continue
        gp, mins, fgm, fga, ftm, fta, pts = (int(r[i]) for i in (2, 4, 6, 7, 12, 13, 15))
        orb, drb, pf, ast, tov, stl, blk = (int(r[i]) for i in (17, 18, 21, 22, 23, 24, 25))

        on_floor = team_poss * mins / (team_min / 5)
        game_score = (pts + 0.4 * fgm - 0.7 * fga - 0.4 * (fta - ftm) + 0.7 * orb + 0.3 * drb
                      + stl + 0.7 * ast + 0.7 * blk - 0.4 * pf - tov)
        shots = fga + 0.44 * fta

        players.append({
            "player": r[1].split("  ")[0],
            "gp": gp,
            "min": mins,
            "pts": pts,
            "ts_pct": round(100 * pts / (2 * shots), 1) if shots else None,
            "usg_pct": round(100 * (shots + tov) / on_floor, 1),
            "pts_100": round(100 * pts / on_floor, 1),
            "reb_100": round(100 * (orb + drb) / on_floor, 1),
            "ast_100": round(100 * ast / on_floor, 1),
            "tov_100": round(100 * tov / on_floor, 1),
            "gmsc": round(game_score / gp, 1),
        })

    if sum(p["pts"] for p in players) != int(total[15]) or sum(p["min"] for p in players) != team_min:
        raise ValueError(f"{team} {season}: player totals don't match team totals")

    players.sort(key=lambda p: -p["min"])
    write_csv(DATA / season / f"{team}-players.csv", players)


def get_player_log(site, player_id, season):
    path = DATA / "raw" / season / "players" / f"{player_id}.json"
    if not path.exists():
        year = season[:4]
        url = f"https://{site}/services/roster_bio_stats.ashx?rp_id={player_id}&sport=mbball&year={year}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    return json.loads(path.read_text())["stats"]["game_by_game_stats"]


def load_game_logs(team, season, team_games):
    html = get_page(TEAMS[team], season)
    start = html.find('id="individual-overall"')
    chunk = html[start:html.find("</table>", start)]
    roster = dict(re.findall(r'data-player-id="(\d+)">([^<]+)<', chunk))
    poss_by_date = {g["date"]: g["poss"] for g in team_games}
    result_by_date = {g["date"]: (g["opponent"], g["result"]) for g in team_games}

    rows = []
    for player_id, name in roster.items():
        for g in get_player_log(TEAMS[team], player_id, season):
            if g["is_a_footer_stat"] or not (g["minutes_played"] or "").isdigit():
                continue
            if g["minutes_played"] == "0":
                continue
            stat = lambda k: int(g[k] or 0)
            mins, pts = stat("minutes_played"), stat("points")
            fgm, fga = stat("field_goals_made"), stat("field_goals_attempted")
            ftm, fta = stat("free_throws"), stat("free_throws_attempted")
            orb, drb = stat("offensive_rebounds"), stat("defensive_rebounds")
            ast, tov, stl, blk, pf = (stat(k) for k in ("assists", "turnovers", "steals", "blocks", "personal_fouls"))

            shots = fga + 0.44 * fta
            on_floor = poss_by_date[g["date"]] * mins / 40
            game_score = (pts + 0.4 * fgm - 0.7 * fga - 0.4 * (fta - ftm) + 0.7 * orb + 0.3 * drb
                          + stl + 0.7 * ast + 0.7 * blk - 0.4 * pf - tov)
            opponent, result = result_by_date[g["date"]]

            rows.append({
                "player": name.strip(),
                "date": g["date"],
                "opponent": opponent,
                "result": result,
                "min": mins,
                "pts": pts,
                "reb": orb + drb,
                "ast": ast,
                "tov": tov,
                "ts_pct": round(100 * pts / (2 * shots), 1) if shots else None,
                "usg_pct": round(100 * (shots + tov) / on_floor, 1),
                "gmsc": round(game_score, 1),
            })

    season_pts = sum(g["us"]["pts"] for g in team_games)
    if sum(r["pts"] for r in rows) != season_pts:
        raise ValueError(f"{team} {season}: player game logs don't add up to team points")

    write_csv(DATA / season / f"{team}-player-games.csv", rows)


def find_conference_games(teams):
    # a GNAC game shows up in both schools' tables with the same date and flipped score
    lookup = {}
    for team, info in teams.items():
        for g in info["games"]:
            key = (g["date"], g["us"]["pts"], g["them"]["pts"])
            lookup.setdefault(key, []).append((team, g))

    matched = {team: [] for team in teams}
    for team, info in teams.items():
        for g in info["games"]:
            key = (g["date"], g["them"]["pts"], g["us"]["pts"])
            options = [(t, h) for t, h in lookup.get(key, []) if t != team]
            if len(options) > 1:
                # two games with the same score on the same night, use the box score to tell them apart
                options = [(t, h) for t, h in options if h["us"] == g["them"]]
            if options:
                opp, their_game = options[0]
                if their_game["us"] != g["them"]:
                    print(f"  note: {team} and {opp} box scores don't agree for {g['date']}")
                matched[team].append((g, opp))
    return matched


def adjust_ratings(games, rounds=100):
    all_games = [g for team_games in games.values() for g, _ in team_games]
    avg = sum(g["ortg"] for g in all_games) / len(all_games)

    off = {t: sum(g["ortg"] for g, _ in gs) / len(gs) for t, gs in games.items()}
    deff = {t: sum(g["drtg"] for g, _ in gs) / len(gs) for t, gs in games.items()}

    # scoring well against a good defense counts for more, and vice versa
    for _ in range(rounds):
        new_off = {t: sum(g["ortg"] * avg / deff[opp] for g, opp in gs) / len(gs) for t, gs in games.items()}
        new_def = {t: sum(g["drtg"] * avg / off[opp] for g, opp in gs) / len(gs) for t, gs in games.items()}
        off, deff = new_off, new_def

    return avg, off, deff


def run_season(season):
    teams = {team: load_team(team, season) for team in TEAMS}
    load_game_logs("Saint Martin's", season, teams["Saint Martin's"]["games"])
    conf_games = find_conference_games(teams)

    for team, gs in conf_games.items():
        if len(gs) < sum(teams[team]["conf"]):
            raise ValueError(f"{team} {season}: only found {len(gs)} conference games")

    avg, off, deff = adjust_ratings(conf_games)

    table = []
    for team, info in teams.items():
        table.append({
            "team": team,
            "record": info["record"],
            "gnac": "%d-%d" % info["conf"],
            "pace": round(info["pace"], 1),
            "ortg": round(info["ortg"], 1),
            "drtg": round(info["drtg"], 1),
            "adj_ortg": round(off[team], 1),
            "adj_drtg": round(deff[team], 1),
            "adj_net": round(off[team] - deff[team], 1),
        })
    table.sort(key=lambda r: -r["adj_net"])
    write_csv(DATA / season / "gnac.csv", table)

    print(f"\n{season}  (GNAC average: {avg:.1f} points per 100)")
    print(f"{'':3}{'team':24}{'record':>7}{'gnac':>7}{'pace':>6}{'ORtg':>7}{'DRtg':>7}{'AdjO':>7}{'AdjD':>7}{'AdjNet':>8}")
    for i, r in enumerate(table, 1):
        print(f"{i:>2} {r['team']:24}{r['record']:>7}{r['gnac']:>7}{r['pace']:>6}{r['ortg']:>7}{r['drtg']:>7}"
              f"{r['adj_ortg']:>7}{r['adj_drtg']:>7}{r['adj_net']:>+8}")


if __name__ == "__main__":
    for season in sys.argv[1:] or ["2024-25", "2025-26"]:
        run_season(season)
