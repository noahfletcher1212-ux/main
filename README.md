# 🏘️ Flip Tycoon — Wholesale Empire

A polished, colorful, cartoon-style **real-estate wholesaling tycoon** game built for
mobile browsers. Find motivated sellers, lock properties under contract below your
max offer, then assign the contract to a cash buyer and pocket a fat wholesale fee —
usually **$10k–$15k a deal**. Reinvest, unlock pricier markets, and climb from
Rookie to Legend.

> No app store, no install, no build step. It's a single static web app — open it and play.

## ▶ Play it

Just open `index.html` in any modern browser (designed phone-first, works on desktop too):

```bash
# from the repo root, serve it locally:
python3 -m http.server 8080
# then visit http://localhost:8080 on your phone or desktop
```

Or simply double-click `index.html`. Your progress auto-saves to the browser.

## 🎮 How it plays

Real wholesaling, gamified into a tight loop:

1. **🔍 Hunt** — send out marketing to generate property leads. Better marketing → more & hotter leads.
2. **🧮 Analyze** — every deal shows its **After-Repair Value**, repair estimate, and the seller's asking price. The game computes your **Max Allowable Offer** using the industry **70% Rule** (`70% of ARV − repairs`).
3. **🤝 Negotiate** — pick a strategy: **Lowball** (big spread, low odds), **Fair** (reliable ~$10–15k), or **Generous** (safe, slim margin). Stay at or below your max offer to lock in profit.
4. **💸 Assign** — multiple cash buyers bid for your contract. Pick the best fee and cash out. (Small chance a buyer gets cold feet — that's wholesaling!)
5. **📈 Reinvest** — buy upgrades, unlock bigger markets, climb the ranks.

Each in-game **day** gives you limited **⚡ energy** (actions). Hunting and negotiating
cost energy; **End Day** to refill. Cold leads can go stale overnight, so work your pipeline.

## ♻️ Replayability

- **Procedurally generated deals** — random addresses, conditions, seller motivations, and numbers every time.
- **4 upgrade tracks** — Marketing Reach, Negotiation Skill, Buyer Network, Hustle Stamina (5 levels each).
- **4 unlockable markets** — Suburbs → City Blocks → Metro High-Rise → Luxury Coast, with progressively bigger homes and fees.
- **7 ranks** — Rookie, Dealer, Closer, Investor, Mogul, Tycoon, Legend.
- **Random events** — referral bonuses, energy drinks, super-motivated sellers, hot-market days.
- **Career stats** — total earned, biggest deal, average per deal, and more.

## 💰 The money system

Wholesale fees scale with the deal: a well-negotiated lead on a motivated seller in the
Suburbs nets roughly **$10k–$15k**. Lowball harder for bigger spreads (at the cost of
acceptance odds), grow your Buyer Network for fatter premiums, and move into Metro and
Luxury markets where single deals can clear six figures.

## 🛠️ Tech

- **Vanilla HTML / CSS / JavaScript** — zero dependencies, zero build tooling.
- Mobile-first responsive layout with safe-area insets, chunky cartoon UI, animated
  gradient background, confetti, count-up cash, and tiny WebAudio sound effects (mutable).
- State persists via `localStorage`.

### Files

```
index.html        # markup + screens
css/styles.css    # cartoon visual system
js/game.js        # all game logic (deals, economics, render, FX)
```

## License

Personal project — play, fork, and remix freely.
