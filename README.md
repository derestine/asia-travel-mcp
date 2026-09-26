# asia-travel-mcp

An MCP server that lets AI agents **discover, book, and manage tours & activities across Asia** — the transaction layer for agentic travel.

Any MCP-capable agent (Claude, custom concierges, …) can search inventory, check live availability, reserve a hold, and confirm/cancel bookings through 7 tools. Inventory comes from partner APIs via a provider-adapter interface, so new suppliers plug in without touching the agent surface.

## Tools

| Tool | What it does |
|---|---|
| `search_activities` | Search tours & activities by destination, date, category, budget |
| `get_activity_details` | Description, highlights, cancellation policy |
| `check_availability` | Live availability + total price for a date |
| `create_booking_hold` | Reserve inventory → returns `hold_id` + `payment_url` |
| `confirm_booking` | Convert a paid hold into a confirmed booking (call from payment webhook) |
| `get_booking` | Look up a booking by reference |
| `cancel_booking` | Cancel upstream + locally |

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
python -m asia_travel_mcp        # runs on stdio
```

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "asia-travel": {
      "command": "/path/to/asia-travel-mcp/.venv/bin/python",
      "args": ["-m", "asia_travel_mcp"],
      "env": { "TRAVEL_PROVIDER": "mock" }
    }
  }
}
```

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `TRAVEL_PROVIDER` | `mock` | `mock` (demo data) or `viator` (live API) |
| `VIATOR_API_KEY` | — | Partner API key from partners.viator.com |
| `TRAVEL_DB_PATH` | `data/bookings.db` | SQLite store for holds & bookings |
| `PAYMENT_LINK_BASE` | stub URL | Hosted checkout base (see below) |
| `HOLD_TTL_MINUTES` | `30` | How long a hold waits for payment |

## Payments

Agents can't hold credit cards, so the flow is:

1. Agent calls `create_booking_hold` → inventory reserved, traveler gets a `payment_url`
2. Traveler pays at that URL
3. Your payment webhook calls `confirm_booking(hold_id)` → booking confirmed

Set `PAYMENT_LINK_BASE` to your hosted checkout (Stripe Payment Links, Paddle).
The default is a clearly-marked stub — replace before handling real money.

## Providers

- **`mock`** — 8 realistic Asia activities (Tokyo, Bangkok, Bali, Taipei, Singapore). Deterministic availability. For demos, tests, development.
- **`viator`** — Viator Partner API (`api.viator.com/partner`). Needs a partner key: sign up at partners.viator.com, then `TRAVEL_PROVIDER=viator VIATOR_API_KEY=…`.

Adding a supplier = one new file implementing `ActivityProvider` in `src/asia_travel_mcp/providers/`.

## Roadmap

- [ ] Hotels via Expedia Rapid / Hotelbeds provider
- [ ] Klook / KKday activities provider (deeper Asia coverage)
- [ ] Developer wallet billing (pre-funded accounts for agent builders)
- [ ] Multi-provider fallback + best-price routing
- [ ] Destination guides (content layer for agent recommendations)
- [ ] `mcpb` bundle for one-click install

## Tests

```bash
pytest   # end-to-end booking flow against the mock provider
```
