# iOS Shortcut: Send bet365 screenshot to GitHub

## Formål

Denne genvej sender et screenshot fra iPhone til repoet `Bendecks/Odds`.

Du vælger selv om billedet er:

- `possible_bets` = odds/markeder der skal vurderes
- `history` = bet365-historik der skal bogføres

## Du skal bruge

1. En GitHub Personal Access Token med adgang til repoet `Bendecks/Odds`.
2. iOS Shortcuts appen.
3. Repoet skal være privat, og token skal ikke deles i ChatGPT.

## GitHub token

Lav token her:

GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens

Anbefalet:

- Repository access: Only selected repositories
- Repository: `Bendecks/Odds`
- Permissions:
  - Contents: Read and write
  - Metadata: Read-only

Gem token sikkert. Den skal indsættes i genvejen som tekstvariabel.

## Shortcut-flow

Navn: `Send bet365 til Odds`

### Handlinger

1. **Take Screenshot**
2. **Choose from Menu**
   - `Mulige bets`
   - `Historik`
3. Hvis `Mulige bets`:
   - Sæt variabel `Type` til `possible_bets`
4. Hvis `Historik`:
   - Sæt variabel `Type` til `history`
5. **Get Current Date**
6. **Format Date**
   - Format: `yyyy-MM-dd_HHmmss`
7. **Set Variable**
   - `Filename` = `[Formatted Date]_[Type].png`
8. **Base64 Encode** screenshot
9. **Text** med JSON-body:

```json
{
  "message": "Upload bet365 screenshot",
  "content": "BASE64_HER"
}
```

10. Erstat `BASE64_HER` med base64-output fra screenshot.
11. **Get Contents of URL**

URL:

```text
https://api.github.com/repos/Bendecks/Odds/contents/inbox/[Type]/[Filename]
```

Method: `PUT`

Headers:

```text
Authorization: Bearer DIN_GITHUB_TOKEN
Accept: application/vnd.github+json
Content-Type: application/json
X-GitHub-Api-Version: 2022-11-28
```

Request Body: JSON fra trin 9.

## Filnavne

Eksempler:

```text
inbox/possible_bets/2026-04-26_114100_possible_bets.png
inbox/history/2026-04-26_181500_history.png
```

## Når filerne ligger i repoet

Skriv i ChatGPT:

- `scan repo nu`
- `scan striks repo nu`
- `bogfør repo`
- `status repo`

## Vigtigt

Upload aldrig din GitHub token til repoet eller til ChatGPT.
