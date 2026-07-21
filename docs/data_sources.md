# Data Sources

## football-data.org API v4

The project currently uses the football-data.org API v4 as its primary source
for 2026 FIFA World Cup competition and match data.

### Retrieved Data

The extraction pipeline retrieves:

- World Cup competition metadata
- Season information
- Match IDs
- Match dates
- Match status
- Tournament stage
- Home and away teams
- Match scores
- Match winners
- Extra-time scores
- Penalty-shootout scores

### API Configuration

The API base URL and credentials are configured through environment variables:

```text
FOOTBALL_DATA_API_KEY
FOOTBALL_DATA_BASE_URL
WORLD_CUP_COMPETITION_CODE
```