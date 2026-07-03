# Nexus News Briefing Studio Design

The user wants a new Nexus window for latest news with videos, transcript lanes, narration, and controls to move between stories. The selected MVP is a reliable "briefing studio": it researches recent headlines, opens a dedicated Nexus news window, presents each story with source/link/video-search slot, shows a three-line briefing transcript lane, and creates a concise narration script.

## Scope

This milestone adds:

- `news.html` Nexus desktop module
- `news_briefing` bridge and structured command
- `open_ui` / natural language routing for `news`, `noticias`, `manchetes`
- structured briefing data in `NexusService`
- Gemini/OpenAI schema updates

The first implementation does not pretend to have true live video transcript extraction. Instead, it builds a trustworthy briefing lane from article title/body/source and gives each story a YouTube search URL for the video slot. Later phases can replace the video search slot with selected clips and real transcript segments.

## Briefing Data

`build_news_briefing(query, limit)` returns:

```json
{
  "ok": true,
  "query": "top news Brasil",
  "generated_at": "2026-05-16T...",
  "items": [
    {
      "index": 1,
      "title": "Headline",
      "source": "Source",
      "published_at": "date",
      "url": "https://...",
      "body": "Short body",
      "summary": "Two sentence summary",
      "video": {
        "provider": "youtube-search",
        "url": "https://www.youtube.com/results?search_query=..."
      },
      "transcript": {
        "past": "Context line",
        "present": "Headline line",
        "future": "What to watch next"
      }
    }
  ],
  "narration": "[Noticia 1] ..."
}
```

The service accepts injected fixture results for tests and uses DuckDuckGo news at runtime when no fixture is supplied.

## UI

The news module uses the current Nexus window frame. The layout is dense and operational:

- left/center video stage with a large "clip slot" and source CTA
- right story rail with headline cards
- transcript lane under the stage with past/present/future rows
- narration summary area under transcript
- controls for previous, next, refresh, and "fale mais"

## Error Handling

If the news search package is unavailable or no results return, the service returns `ok: false` with a readable error and the UI renders an empty state. Links are escaped in UI and bridge responses remain JSON.

## Testing

Use TDD:

- service test for fixture results producing video/transcript/narration
- static module test for UI contract markers
- open-ui test for news module routing
- bridge test for `news_briefing`
- schema/prompt test for `news_briefing`

Then run the full Nexus test slice.
