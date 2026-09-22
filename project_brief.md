# My agent: woj-agent
One-liner: A conversational basketball intelligence agent that helps NBA fans and analysts research live and historical statistics, compare players across eras, and debate basketball arguments with evidence-first reasoning and advanced analytics.

Tool coverage:
- Memory: User debate stances, favorite teams/players, past arguments, and conversational context
- Tools: Basketball Reference scraper for historical box scores and advanced metrics (TS%, rTS%, BPM, VORP, PER, WS/48); live ESPN/NBA API for scores, rosters, schedules, and standings; game log aggregation
- Catalog/UI: Player cards, responsive comparison tables, compact game logs, and trend charts rendered as rich UI components
- Image gen: Matchup graphics and shot charts (optional)
- Sandbox: Derived statistical calculations (TS%, eFG%, rTS%, AST/TO ratio, Net Rating, possession-adjusted metrics)

Core rails (everyone): memory, tools, eval, deploy, frontend
My stretch menu (pick later): Catalog/UI, Sandbox
First eval question: "Compare 2016 Curry to 2025 SGA in scoring efficiency and era-adjusted context" -> returns accurate TS%, rTS%, BPM, and balanced stylistic breakdown without hallucinating numbers.
