# JohnnyBets Media Generation

This document covers the image and video generation capabilities for the marketing agent.

## Overview

The marketing agent generates promotional content using:
- **Images**: Gemini 3 Pro via OpenRouter (best quality, ~25s)
- **Videos**: xAI Grok Imagine (async, ~30-60s)

Generated media is automatically stored to Azure Blob Storage (or local filesystem as fallback) and can be posted directly to X.

## API Specifications

### Image Generation (Gemini 3 Pro)

| Feature | Specification |
|---------|--------------|
| **Model** | google/gemini-3-pro-image-preview |
| **Provider** | OpenRouter |
| **Speed** | ~20-30 seconds |
| **Quality** | Excellent text rendering, creative layouts |
| **Aspect Ratios** | 16:9, 9:16, 1:1, 4:3, 3:4, etc. |

### Video Generation (xAI)

| Feature | Specification |
|---------|--------------|
| **Model** | grok-imagine-video |
| **Provider** | xAI |
| **Speed** | Async with polling, ~30-60 seconds |
| **Resolution** | 720p or 480p |
| **Duration** | 1-15 seconds |

### Environment Variables

```
OPENROUTER_API_KEY=...   # Required for image generation
XAI_API_KEY=...          # Required for video generation
```

## Style Presets

Minimal prompts — let the model do the work.

| Preset | Prompt | Best For |
|--------|--------|----------|
| `matchup` | Bold sports matchup. Black bg. Diagonal color clash. Giant type. Stats with labels. | Game day, matchups |
| `terminal` | Terminal on black. ASCII art logos. Monospace. Team colors. No chrome. | Analytics, threads |
| `stats` | Sports stat card. Dark bg. Clean data layout. Team color accents. | Stat cards, trends |
| `promo` | Dynamic sports promo. Bold type with motion. Colors collide. Stats animate. | Videos, promos |
| `hype` | Athletic campaign aesthetic. Diagonal slash. Massive bold type. Motion streaks. | Hero graphics |

## Tips

- **Text**: ALL CAPS for headlines, include specific numbers with labels
- **Colors**: Mention team colors ("purple gold vs navy")
- **Terminal**: Say "no window chrome" to avoid bezels
- **Video**: Describe motion ("stats scroll up")

## Marketing Agent Tools

### `generate_promo_image`

Generate a static promotional image.

**Parameters:**
- `prompt` (required): Description of the image content
- `style`: Style preset (default: "matchup")
- `aspect_ratio`: Image dimensions (default: "16:9")

**Example:**
```
Generate a promo image for tomorrow's Lakers @ Nuggets game.
Prompt: "Lakers vs Nuggets NBA matchup. LAL VS DEN typography. Stats: DEN -6.5 spread, 72% model edge. Purple and gold vs navy blue team colors."
Style: matchup
```

### `generate_promo_video`

Generate a promotional video (up to 15 seconds).

**Parameters:**
- `prompt` (required): Description of video content and motion
- `style`: Style preset (default: "matchup")
- `duration`: Length in seconds (default: 6, max: 15)
- `aspect_ratio`: Video dimensions (default: "16:9")

**Example:**
```
Generate a promo video for the Lakers @ Nuggets game.
Prompt: "Lakers vs Nuggets promo. Purple and gold collide with navy blue. LAL VS DEN flies in. Stats scroll: SPREAD DEN -6.5, EDGE 72%, JOKIC 27.2 PPG. JohnnyBets.AI logo fades in."
Style: matchup
Duration: 10
```

### `post_to_x_with_media`

Post a tweet with an attached image or video.

**Parameters:**
- `text` (required): Tweet text (max 280 chars)
- `media_url` (required): URL from generate_promo_image/video
- `reply_to`: Optional tweet ID to reply to

**Example:**
```
Post to X with the generated image.
Text: "Lakers @ Nuggets tonight. Denver's been cooking at home. 9-1 last 10. The numbers say something. johnnybets.ai"
Media URL: [url from generate_promo_image]
```

## Prompt Engineering Tips

### For Images

1. **Lead with style/format**: "High impact sports matchup graphic" or "Modern terminal aesthetic"
2. **Specify typography**: "Bold condensed typography LAL VS DEN"
3. **Include team colors**: "Purple and gold vs navy blue"
4. **Add stats with labels**: "SPREAD: DEN -6.5 | EDGE: 72%"
5. **End with branding**: Tool automatically appends "JohnnyBets.AI | Bet responsibly 21+"

### For Videos

1. **Describe motion**: "Stats scroll up one by one", "Typography slams in"
2. **Sequence events**: "Opens with title, then stats appear, ends with logo"
3. **Include visual effects**: "Motion blur", "particle effects", "energy streaks"
4. **Keep it dense**: More content = more engaging video

### Text Rendering

xAI's model handles text well. For best results:
- Use ALL CAPS for headlines
- Keep stat labels short (SPREAD, EDGE, O/U)
- Include specific numbers (not "high probability" but "72%")

## Example Prompts

### Game Day Matchup (Image)
```
Lakers vs Nuggets NBA matchup. Bold diagonal slash of purple and gold colliding with navy blue. Giant condensed typography LAL VS DEN. Stats: DEN -6.5 | 72% EDGE. Athletic campaign aesthetic, premium sports marketing.
```

### Terminal Style (Image)
```
Clean terminal on black background. Celtics vs Bucks. ASCII art shamrock and deer logos made of text characters. Monospace green text: CELTICS @ BUCKS | BOS +2.5 (65%). Modern dev tool aesthetic.
```

### Stats Scroll (Video)
```
Sports analytics promo video. Dark background with purple and gold energy. Opens with LAL VS DEN title. Stats scroll one by one: SPREAD: DEN -6.5, TOTAL: 228.5, EDGE: 72%, TREND: DEN 9-1 L10. Each stat has motion entrance. Ends with JohnnyBets.AI logo.
```

## Storage

Generated media is stored in:
- **Azure Blob Storage**: `marketing-media` container, organized by date
- **Local fallback**: `./data/marketing-media/YYYY/MM/DD/`

Files are named with UUIDs to prevent collisions.

## Environment Variables

```bash
# Required
XAI_API_KEY=your-xai-api-key

# Optional (for Azure storage)
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
MEDIA_STORAGE_CONTAINER=marketing-media

# Optional (for local storage)
LOCAL_MEDIA_DIR=./data/marketing-media
```

## Rate Limits & Costs

- **Images**: ~$0.02-0.04 per image
- **Videos**: ~$0.10-0.20 per video (varies by duration)
- **Rate limits**: Check xAI console for current limits

## Error Handling

The tools return JSON with either:
- `{"status": "success", ...}` with URLs and metadata
- `{"status": "error", "error": "description"}` on failure

Common errors:
- `XAIMediaError`: API issues (auth, rate limits, content policy)
- `XMediaUploadError`: X media upload issues
- Timeout errors for video generation (default 120s max wait)
