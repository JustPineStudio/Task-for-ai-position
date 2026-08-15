# Lexi Lens

CLI aplikacija koja dohvati stvarni Lexi blog post, profilira njegovu svrhu i pokrene provjerljivi
multi-agent urednički panel. Rezultat nije samo ocjena: uključuje osporene procjene,
tri prioritetne promjene i konkretne prijedloge prije/poslije.

## Brzi početak

Potrebni su Python 3.11+ i OpenAI API ključ.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
```

U `.env` upišite `OPENAI_API_KEY`, zatim:

```bash
lexi-lens evaluate "https://lexi.hr/psiholoski-mehanizmi-iza-clickbaita/" --output output/result.json
```

Za stvarni komunikacijski zadatak možete dostaviti opcionalni JSON brief:

```bash
lexi-lens evaluate URL --brief brief.example.json --output output/result.json
```

Brief zadaje publiku, cilj, ton, kanal i željenu radnju te ima prednost pred automatskom detekcijom.

Model se bira s `--model` ili `LEXI_LENS_MODEL`; zadana vrijednost je `gpt-5.6-luna`. Standardno
pokretanje radi šest modelskih poziva: profil, četiri paralelna evaluatora i završnu sintezu. Time je
trošak predvidljiv i razuman za zadatak.

API ključ se čita isključivo iz `OPENAI_API_KEY`. `.env` je u `.gitignore`; `.env.example` sadrži samo
placeholder. Prije objave provjerite da `git ls-files .env` ne vraća ništa. Ključ se nikad ne ispisuje,
ne sprema u JSON rezultat i ne šalje u logove.

## Kako radi

```text
Lexi URL → čisti članak → profil vrste/publike/cilja
                              ↓
                 4 evaluatora (paralelno)
                              ↓
                 provjera citata + 1 korektivni pokušaj
                              ↓
                 deterministička agregacija
                              ↓
                 adversarial reviewer → korekcije
                              ↓
                 3 prioriteta + provjereni before/after → JSON/terminal
```

Svaki agent daje 0–100 po četiri unaprijed definirana kriterija. Kriteriji imaju vlastite težine, a
ukupna ocjena računa se u Pythonu. Time peti LLM ne može proizvoljno promijeniti rezultat. Ako bilo
koji agent vrati pogrešnu shemu ili rubriku, analiza ne proizvodi varljiv djelomični score.

Svaki citat normalizira se za Unicode navodnike, crtice i razmake te se traži u izvornom članku.
Nepostojeći citat pokreće jedan korektivni pokušaj, nakon čega analiza pada. Isto pravilo vrijedi za
`before` tekst u prijedlozima izmjena. Kritičar ne daje novu proizvoljnu ocjenu: mora imenovati
postojećeg agenta i kriterij te predložiti ograničenu korekciju od ±30 bodova.

Detalji odluka su u [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), plan u
[docs/PLAN.md](docs/PLAN.md), a promptovi i razvoj prompta u [docs/PROMPTS.md](docs/PROMPTS.md).

## Testovi i kvaliteta

```bash
pytest
ruff check .
```

Testovi ne trebaju mrežu ni API ključ. Pokrivaju URL i redirect zaštitu, ekstrakciju, paralelno
izvršavanje, matematiku, retry citata, Unicode normalizaciju, kritičara, pouzdanost, prioritete i
odbijanje izmišljenog `before` ulomka.

## Primjer rezultata

[`output/example.json`](output/example.json) sadrži referentnu AI-potpomognutu procjenu stvarnog Lexi
članka o clickbaitu. Tijekom pripreme repozitorija API ključ nije bio dostupan, pa datoteka pošteno
navodi da nije nastala API pozivom. Pokretanje gornje naredbe stvara pravi rezultat aplikacije u istom
formatu; tu datoteku treba zamijeniti prije konačne predaje kako bi zahtjev za primjerom pokretanja bio
ispunjen bez dvosmislenosti.

## Kalibracija s ljudskim urednicima

```bash
lexi-lens benchmark output evals/human-labels.example.json
```

Benchmark računa MAE, RMSE i udio AI ocjena unutar ±5 bodova od ljudske ocjene. Format oznaka nalazi
se u `evals/human-labels.example.json`.

## Dodatni izlazi

- odvojene ocjene pisanja, publike, cilja i vjerodostojnosti te publish readiness
- lokalne metrike rečenica, odlomaka, ponavljanja, strukture i vremena čitanja
- ocjena uvoda i svake sekcije, uz označen najslabiji dio
- rewrite presuda `better`, `different` ili `worse` uz provjeru značenja, tona i novih tvrdnji

## Ograničenja i idući koraci

- LLM ocjene prirodno variraju; za produkciju treba kalibracijski skup s ljudskim urednicima.
- Prikazana pouzdanost nije statistički dokaz točnosti; stvarnu kvalitetu treba mjeriti ljudskim evalom.
- Agenti procjenjuju potporu tvrdnjama unutar članka, ali ne rade vanjski fact-checking.
- Za proizvoljno duge dokumente trebalo bi dodati segmentiranje bez gubitka globalne strukture.
- Trenutno je alat namjerno ograničen na Lexi domenu, čime se smanjuje SSRF površina.
