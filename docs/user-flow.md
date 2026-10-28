# De-Influence AI — User Interaction Flow

For pitching and presentation. Paste this Mermaid block into any Mermaid viewer
(e.g. mermaid.live) or a Markdown renderer that supports Mermaid to see the diagram.

```mermaid
flowchart TD
    Start([User opens De-Influence AI<br/>installable PWA, works offline]) --> Home[Analyse page]

    Home --> Input{How to add an item?}
    Input -->|Paste Shopee/TikTok/Shein link| Link[POST /api/check-link]
    Input -->|Tap a demo item| Demo[POST /api/scan]

    Link --> Resolve[[link_resolver<br/>NO network fetch SSRF-safe<br/>parse URL then look up SQLite]]
    Resolve --> Match{Exact demo link<br/>in catalogue?}
    Match -->|Yes| Product[(SQLite product + reviews)]
    Match -->|No| Emulate[Deterministic map to a<br/>representative item<br/>labelled EMULATED]
    Emulate --> Product
    Demo --> Product

    Product --> Engine[[Analysis pipeline]]
    Engine --> E1[Defect NLP<br/>Malaysian code-switch lexicon]
    Engine --> E2[Hype-cycle decay<br/>Gompertz forecast]
    Engine --> E3[TrueCost<br/>Cost-Per-Wear]
    E1 --> Fuse[Fuse to Longevity Score<br/>+ Regret Probability]
    E2 --> Fuse
    E3 --> Fuse
    Fuse --> Persona[Apply saved preferences<br/>to personalized note]
    Persona --> Verdict[/KEEP CONSIDER CAUTION AVOID<br/>with explainable breakdown + disclaimers/]

    Verdict --> Save[(Save to private browser history)]
    Verdict --> Act{User action}
    Act -->|Add to compare| Compare[Compare page side-by-side]
    Act -->|Wishlist| Wish[Wishlist page stock + email coming soon]
    Save --> Dash[Dashboard page patterns and flow]

    Home -.nav.-> Personalize[Personalize page style colour budget to SQLite]
    Home -.nav.-> Why[Why Us page competitor matrix + value props]
    Home -.nav.-> Valid[Validation page F1 MAE + download dataset xlsx]
    Home -.nav.-> Dbg[[Debug page only if DEINFLUENCE_DEBUG=1]]

    Personalize -.feeds.-> Persona
```

## Narration for the pitch

1. **Open** — the app installs as a PWA and works offline.
2. **Analyse** — the shopper pastes a product link (or taps a demo). We never fetch the live
   page (platform restrictions + SSRF safety); the link resolves against our own SQLite catalogue,
   with unknown links clearly labelled as an emulated demo.
3. **Engines** — three signals run: localized Malaysian defect NLP, Gompertz trend-decay, and
   Cost-Per-Wear. They fuse into an explainable Longevity Score and Regret Probability, then a
   personalization note is applied from saved preferences.
4. **Verdict** — KEEP / CONSIDER / CAUTION / AVOID, with the score breakdown and responsible-use
   disclaimers. The result is saved to the shopper's private, on-device history.
5. **Act** — add to compare, add to wishlist, or review patterns on the dashboard.
6. **Trust pages** — Why Us (market positioning), Validation (real F1/MAE + downloadable dataset),
   and a terminal-toggled Debug page for live inspection.
