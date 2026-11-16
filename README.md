# GNAC Basketball Efficiency Ratings

Team and player efficiency ratings for GNAC men's basketball (NCAA D2), built from each school's posted box scores.

## 2025-26

| # | Team | GNAC | Adj ORtg | Adj DRtg | Adj Net |
|---|---|---|---|---|---|
| 1 | Saint Martin's | 15-3 | 113.2 | 98.1 | +15.1 |
| 2 | Alaska Anchorage | 12-6 | 108.2 | 101.0 | +7.2 |
| 3 | Central Washington | 9-9 | 110.0 | 104.8 | +5.2 |
| 4 | Montana State Billings | 9-9 | 110.8 | 111.2 | -0.4 |
| 5 | Seattle Pacific | 9-9 | 105.7 | 106.2 | -0.5 |
| 6 | Northwest Nazarene | 12-6 | 106.5 | 107.9 | -1.4 |
| 7 | Western Washington | 7-11 | 113.3 | 116.4 | -3.1 |
| 8 | Alaska Fairbanks | 9-9 | 107.5 | 111.0 | -3.5 |
| 9 | Simon Fraser | 4-14 | 106.5 | 116.1 | -9.7 |
| 10 | Western Oregon | 4-14 | 101.2 | 113.3 | -12.1 |

Points scored (ORtg) and allowed (DRtg) per 100 possessions, adjusted for opponent strength. Net is the difference.

## How it works

- **Possessions** = FGA − offensive rebounds + turnovers + 0.475 × FTA
- **Ratings** = points per 100 possessions, so fast and slow teams compare fairly.
- **Adjustment**: scoring against a good defense counts for more, against a bad one for less. Repeated until the numbers settle.

Player ratings (true shooting %, usage %, per-100 stats, Game Score) and full tables for 2024-25 and 2025-26 are in `data/`.

Game-by-game player ratings for Saint Martin's are in `data/<season>/Saint Martin's-player-games.csv`.

## Run it

```
python3 efficiency.py
```

Python 3 only, no extra packages.
