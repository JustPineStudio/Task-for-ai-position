# Plan izrade

## Cilj i kriteriji uspjeha

Ulaz je jedan HTTPS URL na `lexi.hr`. Aplikacija mora izdvojiti samo sadržaj članka, poslati ga
neovisnim evaluatorima, dati usporedivu ocjenu i pokazati dokaze iza svake procjene. Uspjeh nije
"zvuči uvjerljivo", nego ponovljiv proces: ista rubrika, validirana struktura odgovora i matematički
transparentna agregacija.

## Faze

1. Dohvat i ekstrakcija: validacija domene, ograničeni HTTP klijent i ekstrakcija glavnog teksta.
2. Evaluacija: četiri specijalizirana prompta pokreću se paralelno nad identičnim sadržajem.
3. Validacija: Pydantic provjerava raspon ocjena, broj kriterija, dokaze i identitet agenta.
4. Agregacija: kod računa težinski prosjek kriterija i agenata; LLM ne određuje konačnu ocjenu.
5. Prezentacija: sažetak u terminalu te puni JSON za reviziju i daljnju obradu.
6. Provjera: unit testovi za URL zaštitu, ekstrakciju, konkurentnost i matematiku ocjene.

## Druga iteracija: diferencijacija

Implementirana je kao eksplicitan pipeline, redom:

1. programska validacija citata uz jedan retry,
2. profiliranje vrste sadržaja, publike i cilja,
3. adversarial reviewer s ograničenim korekcijama,
4. mjerenje neslaganja (ponovljeno uzorkovanje je kasnije uklonjeno radi troška),
5. deduplicirana lista točno tri najvažnije promjene,
6. provjerljivi prijedlozi prije/poslije.

Namjerno nisu uvedeni dodatni agenti samo radi većeg broja. Svaka nova faza ima zasebnu odgovornost,
strukturiranu shemu, programsku validaciju i jasan failure mode.

## Treća iteracija: urednički proizvod i kalibracija

1. Opcionalni brief daje stvarni cilj, publiku, ton, kanal i željenu radnju.
2. Rezultat se razdvaja na pisanje, publiku, cilj i vjerodostojnost uz publish readiness.
3. Lokalni diagnostics sloj računa objektivne signale bez dodatnog API poziva.
4. Članak se lokalno dijeli na uvod i Markdown sekcije te označava najslabiji dio.
5. Završna sinteza provjerava je li svaki rewrite bolji i siguran u istom strukturiranom pozivu.
6. Offline benchmark uspoređuje rezultate s ljudskim ocjenama kroz MAE, RMSE i prag ±5.

Vanjski fact-checking ostaje zaseban budući korak jer zahtijeva pretraživanje, procjenu kvalitete izvora,
citiranje i jasnu kontrolu dodatnog troška. Ne treba ga skrivati unutar osnovne ocjene pisanja.

Nakon dobivanja konačnih uputa orkestracija je pojednostavljena s približno 14 na 6 modelskih poziva:
jedan profil, četiri paralelna evaluatora i jedna završna sinteza. To je bolji omjer kvalitete, čitljivosti
i troška za opseg zadatka.

## Pretpostavke i svjesna ograničenja

- Članak stane u kontekst odabranog modela; produkcijska verzija trebala bi imati map-reduce za vrlo
  dugačke dokumente.
- Evaluatori analiziraju kvalitetu pisanja, a ne provjeravaju istinitost izvora na webu.
- LLM ocjenjivanje nije savršeno deterministično. Fiksna rubrika, strukturirani izlaz i kodna
  agregacija smanjuju varijaciju; ozbiljna produkcijska verzija trebala bi dodati kalibracijski skup.
- CLI je namjeran izbor za opseg zadatka: minimalno sučelje, lako automatiziranje i puni fokus na
  scraping, agente, promptove i objašnjiv rezultat.

## Plan evaluacije sustava

Za kalibraciju bi 20–30 članaka ocijenila najmanje dva ljudska urednika istom rubrikom. Mjerili bismo
slaganje ljudi međusobno, zatim odstupanje svakog agenta od medijana ljudi, stabilnost kroz tri
ponovljena pokretanja i postotak citata koji stvarno postoje u ulazu. Tek nakon toga mijenjali bismo
težine ili promptove, na odvojenom skupu članaka kako ne bismo prilagodili sustav jednom primjeru.
