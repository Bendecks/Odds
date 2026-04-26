# iOS Genvej på dansk: Send bet365 screenshot til GitHub

Denne guide er skrevet til din iPhone 17 med dansk iOS / appen **Genveje**.

Målet er:

1. Du tager et screenshot på iPhone.
2. Du trykker **Del**.
3. Du vælger genvejen **Send bet365 til Odds**.
4. Du vælger om billedet er **Mulige bets** eller **Historik**.
5. Billedet uploades til GitHub-repoet `Bendecks/Odds`.

## Før du bygger genvejen

Du skal bruge en GitHub fine-grained token.

Lav den i GitHub:

**GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens**

Anbefalet opsætning:

- Repository access: **Only selected repositories**
- Repository: **Bendecks/Odds**
- Permissions:
  - **Contents: Read and write**
  - **Metadata: Read-only**

Gem token sikkert. Del den ikke med ChatGPT og læg den ikke i repoet.

---

# Byg genvejen på dansk i iOS

## 1. Opret genvej

Åbn appen **Genveje**.

Tryk **+**.

Navngiv genvejen:

```text
Send bet365 til Odds
```

Tryk på **i** / informationsknappen nederst eller øverst afhængigt af din iOS-version.

Slå til:

```text
Vis i Delingsark
```

Under inputtyper skal den acceptere:

```text
Billeder
```

Hvis du kan vælge flere typer, så vælg også:

```text
Filer
```

---

## 2. Modtag input fra Delingsark

Første handling skal være:

```text
Modtag [Billeder] fra Delingsark
```

På nogle danske iOS-versioner står der i stedet noget tæt på:

```text
Modtag input fra Delingsark
```

Det vigtige er, at genvejen bruger det billede, du deler ind i genvejen.

---

## 3. Vælg type screenshot

Tilføj handlingen:

```text
Vælg fra menu
```

Opret to valg:

```text
Mulige bets
Historik
```

Under **Mulige bets** tilføjer du handlingen:

```text
Tekst
```

Tekstindhold:

```text
possible_bets
```

Tilføj derefter:

```text
Indstil variabel
```

Variabelnavn:

```text
Type
```

Under **Historik** gør du det samme, men tekstindholdet skal være:

```text
history
```

og variablen skal igen hedde:

```text
Type
```

---

## 4. Lav dato til filnavn

Efter menuen tilføjer du:

```text
Aktuel dato
```

Tilføj derefter:

```text
Formatér dato
```

Tryk på formatet og vælg **Specielt** / **Brugerdefineret**, hvis iOS tilbyder det.

Brug formatet:

```text
yyyy-MM-dd_HHmmss
```

Tilføj handlingen:

```text
Tekst
```

Teksten skal sammensættes af variabler sådan her:

```text
[Formateret dato]_[Type].png
```

Du skal ikke skrive klammerne. Indsæt variablerne fra Genveje.

Tilføj:

```text
Indstil variabel
```

Variabelnavn:

```text
Filename
```

---

## 5. Base64-kod billedet

Tilføj handlingen:

```text
Base64-kod
```

Hvis handlingen viser valg mellem kod/afkod, skal den stå til:

```text
Kod
```

Input skal være:

```text
Genvejsinput
```

altså billedet fra Delingsark.

Tilføj:

```text
Indstil variabel
```

Variabelnavn:

```text
Base64
```

---

## 6. Lav JSON til GitHub

Tilføj handlingen:

```text
Tekst
```

Indhold:

```json
{
  "message": "Upload bet365 screenshot",
  "content": "[Base64]"
}
```

Du skal indsætte **Base64** som variabel i stedet for `[Base64]`.

Tilføj:

```text
Indstil variabel
```

Variabelnavn:

```text
Body
```

---

## 7. Lav upload-URL

Tilføj handlingen:

```text
Tekst
```

Indhold:

```text
https://api.github.com/repos/Bendecks/Odds/contents/inbox/[Type]/[Filename]
```

Du skal indsætte **Type** og **Filename** som variabler i stedet for `[Type]` og `[Filename]`.

Tilføj:

```text
Indstil variabel
```

Variabelnavn:

```text
UploadURL
```

---

## 8. Upload til GitHub

Tilføj handlingen:

```text
Hent indhold af URL
```

URL skal være variablen:

```text
UploadURL
```

Tryk **Vis mere**.

Sæt metode til:

```text
PUT
```

Headers:

```text
Authorization: Bearer DIN_GITHUB_TOKEN
Accept: application/vnd.github+json
Content-Type: application/json
X-GitHub-Api-Version: 2022-11-28
```

Erstat `DIN_GITHUB_TOKEN` med din rigtige token direkte i genvejen.

Body / Anmodningstekst skal være:

```text
JSON
```

Indsæt variablen:

```text
Body
```

Hvis Genveje ikke vil acceptere Body som JSON direkte, så vælg i stedet **Fil** eller **Tekst** som anmodningstekst og brug variablen **Body**. Det afhænger lidt af dansk iOS-version.

---

## 9. Slut med besked

Tilføj handlingen:

```text
Vis notifikation
```

Tekst:

```text
Sendt til Odds
```

---

# Brug

1. Åbn bet365.
2. Tag screenshot.
3. Åbn screenshotet.
4. Tryk **Del**.
5. Vælg **Send bet365 til Odds**.
6. Vælg **Mulige bets** eller **Historik**.

Filen lander i en af disse mapper:

```text
inbox/possible_bets/
inbox/history/
```

# ChatGPT-kommandoer

Når der er uploads i repoet, kan du skrive:

```text
scan repo nu
scan striks repo nu
bogfør repo
status repo
```

# Vigtigt

- Upload aldrig token til repoet.
- Send aldrig token i ChatGPT.
- Hvis upload fejler, er det næsten altid enten token-rettigheder, forkert URL, eller Body der ikke er sendt som gyldig JSON.
