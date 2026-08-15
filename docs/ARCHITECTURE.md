# Arhitekturne odluke

## ADR-001: Specijalizirani agenti umjesto više općih sudaca

Četiri perspektive namjerno se malo preklapaju, ali svaka ima drugačije primarno pitanje:

| Agent | Pitanje | Težina |
|---|---|---:|
| Arhitekt teksta | Može li čitatelj pratiti argument od obećanja do zaključka? | 30% |
| Psiholog čitatelja | Zadržava li tekst pažnju i stvara li vrijednost bez manipulacije? | 25% |
| Urednik jasnoće | Je li svaka ideja razumljiva, precizna i ekonomična? | 25% |
| Skeptični strateg | Zaslužuje li tekst povjerenje i daje li nešto primjenjivo? | 20% |

Struktura ima najveću težinu jer loš put kroz tekst umanjuje vrijednost svih dobrih rečenica. Ostale
težine sprečavaju da zabavan, ali nejasan ili neutemeljen tekst dobije previsoku ocjenu.

## ADR-002: Deterministički agregator

Svaki kriterij dobiva 0–100. Rezultat agenta je težinski prosjek njegovih kriterija, a ukupna ocjena
težinski prosjek agenata. Konačna slova su A ≥ 90, B ≥ 80, C ≥ 70, D ≥ 60 i F < 60. LLM daje
semantički sud; aplikacijski kod radi aritmetiku. Time je račun potpuno vidljiv u JSON-u.

## ADR-003: Dokaz je obavezan dio ocjene

Svaki kriterij mora imati 1–3 kratka citata, obrazloženje i prijedlog poboljšanja. Strukturirani izlaz
sprječava tiho izostavljanje polja. Aplikacija još ne provjerava doslovno postojanje citata jer modeli
ponekad normaliziraju navodnike ili razmake; to je prvi sljedeći guardrail za produkciju.

## ADR-004: Paralelni pozivi

Perspektive su neovisne, pa se pozivi izvršavaju s `asyncio.gather`. Latencija je približno jednaka
najsporijem agentu umjesto zbroju četiri poziva. Ako jedan agent ne vrati validan rezultat, cijela
analiza pada: djelomičan ukupni rezultat s pogrešnim težinama bio bi varljiv.

## ADR-005: Siguran, usko ograničen scraper

Prihvaća se samo HTTPS na `lexi.hr` ili poddomenama. Provjerava se i konačni URL nakon redirecta.
Trafilatura odvaja glavni tekst od navigacije i footera, dok BeautifulSoup dohvaća metapodatke.

## ADR-006: Profil prije ocjenjivanja

Prvi strukturirani poziv određuje dominantnu vrstu sadržaja, publiku, cilj i fazu čitatelja. Osnovna
rubrika ostaje ista radi usporedivosti, ali agenti je tumače kroz cilj: dokaz rezultata važniji je za
case study, poučavanje za edukativni tekst, a vođenje prema odluci za prodajni sadržaj.

## ADR-007: Dokazi su izvršna ograničenja

Citati i `before` ulomci normaliziraju se za Unicode, navodnike, crtice i whitespace, a zatim se
programski traže u izvorniku. Evaluator dobiva jedan korektivni pokušaj; ponovljena pogreška prekida
analizu. Time objašnjivost nije samo promptna želja nego provjerljivo pravilo.

## ADR-008: Kritičar ima ograničenu ovlast

Adversarial reviewer vidi profil, članak i agregirane procjene. Može osporiti samo postojeći par
agent/kriterij i predložiti korekciju između -30 i +30. Kod provjerava referencu i ponovno računa
ponderirani rezultat. Kritičar ne može dodati novu rubriku ili izravno postaviti ukupni score.

## ADR-009: Jedan uzorak po agentu radi kontrole troška

Svaki od četiri agenta radi jednu procjenu. Ponovljeno uzorkovanje uklonjeno je iz glavnog toka jer
linearno povećava trošak, a zadatak traži nekoliko poziva. Stvarnu pouzdanost mjeri offline benchmark
s ljudskim urednicima, ne dodatni pozivi u svakom korisničkom pokretanju.

## ADR-010: Jedna završna sinteza

Nakon profila i četiri paralelna evaluatora jedan strukturirani poziv konsolidira dimenzije, segmente,
osporavanja i tri rewrite prioriteta. Ukupno je šest poziva. Matematika, segmentiranje, text diagnostics
i provjera doslovnih citata ostaju u Pythonu.

## ADR-011: Sinteza je usmjerena na akciju

Završni urednik spaja duplikate i vraća točno tri prioriteta. Svaki mora navesti utjecaj, akciju,
izvorne agente i 1–2 prije/poslije izmjene. `before` mora doslovno postojati u članku; `after` ne smije
izmišljati činjenice ni mijenjati autorov glas.

## ADR-012: Brief nadjačava inferenciju

Korisnički JSON brief ima prednost pred modelskom detekcijom. Izvorni brief sprema se odvojeno kako
bi se razlikovalo što je zadano, a što zaključeno.

## ADR-013: Objektivne metrike nisu automatski sud

Duljine, ponavljanja, struktura i obraćanje računaju se lokalno i šalju kao dokazi. Ne pretvaraju se
izravno u kaznene bodove jer duga rečenica može biti namjeran stilski izbor.

## ADR-014: Segmenti i rewriteovi imaju guardrailove

Segment ID-jeve proizvodi kod, a model ih mora vratiti sve i istim redoslijedom. Rewrite validator je
odvojen od autora prijedloga kako bi otkrio promjenu značenja, tona ili nove tvrdnje.
