# vanerpinsights.nl

Website van Van Erp Insights, in het Nederlands (standaard), Engels en Duits.

## Hoe het werkt

Je past teksten en instellingen aan, en `build.py` maakt daar de echte pagina's van in `dist/`. De site draait op Netlify: bij elke push naar `main` bouwt Netlify de site opnieuw en zet hem online (instellingen in `netlify.toml`). Het domein en de e-mail staan bij Strato.

| Wat | Waar |
|---|---|
| Teksten per taal | `src/i18n/nl.json`, `en.json`, `de.json` |
| Contactgegevens, boekingslink, statistieken | `site.json` |
| Opbouw van de pagina's | `src/templates/` |
| Opmaak, afbeeldingen, fonts | `static/` |
| Build en headers voor Netlify | `netlify.toml` |

De pagina's die eruit komen:

- `/`, `/en/`, `/de/`: homepage
- `/privacy/`, `/en/privacy/`, `/de/privacy/`: privacyverklaring
- `/404.html`, `sitemap.xml`, `robots.txt`

## Lokaal bekijken

```
python3 build.py
python3 -m http.server 8000 --directory dist
```

Open daarna http://localhost:8000.

## Publiceren

Push naar `main`. Netlify bouwt en publiceert dan automatisch. In het Netlify-dashboard zie je onder *Deploys* of het gelukt is.

## Instellingen in `site.json`

- `booking_url`: leeg laten. "Plan een kennismaking" opent dan een voorbereide e-mail. Wil je later toch een afsprakenpagina, vul dan hier de link in.
- `plausible_domain`: vul `vanerpinsights.nl` in zodra je een account bij Plausible hebt. Het script en de alinea in de privacyverklaring worden dan automatisch toegevoegd.
- `privacy_updated`: datum die bovenaan de privacyverklaring staat.
