# Promptovi i proces planiranja

Izvorni promptovi aplikacije verzionirani su u [`src/lexi_lens/prompts.py`](../src/lexi_lens/prompts.py),
a definicije svih agenata i rubrika u [`src/lexi_lens/agents.py`](../src/lexi_lens/agents.py). To je
namjerno: dokumentacija opisuje razmišljanje, a izvršni prompt ostaje jedini izvor istine.

## Prompt korišten za AI planiranje

> Osmisli malu Python aplikaciju za procjenu Lexi blog posta. Mora sigurno dohvatiti URL, izvući samo
> članak, pokrenuti najmanje tri neovisna LLM evaluatora i vratiti objašnjivu ukupnu ocjenu. Predloži
> perspektive koje zajedno pokrivaju strukturu, psihologiju čitatelja, jasnoću i vjerodostojnost.
> Izbjegni lažnu preciznost: definiraj rubrike, kalibraciju, dokaze i determinističku agregaciju.
> Rješenje mora biti testabilno bez mreže i dokumentirati trade-offove.

## Kako je prompt evoluirao

Prva ideja bila je tražiti slobodan esej od svakog agenta i zatim prepustiti završnom agentu da odredi
ocjenu. Odbačena je jer skriva račun i uvodi dodatnu varijabilnost. Završni prompt zato:

- daje sidra za skalu (što znači 90, 75 ili 40),
- zahtijeva iste nazive i redoslijed kriterija,
- zahtijeva dokaz iz dostavljenog teksta,
- zabranjuje zaključivanje iz reputacije brenda,
- odvaja semantičku procjenu od aritmetike.

## Promptovi druge iteracije

Pipeline u konačnoj verziji ima tri tipa prompta:

1. `profile`: opisuje zadatak sadržaja bez ocjenjivanja,
2. `evaluation`: primjenjuje stabilnu rubriku kroz detektirani kontekst,
3. `synthesis`: u jednom odgovoru osporava neutemeljene procjene, procjenjuje segmente, izvodi četiri
   dimenzije te deduplicira nalaze u tri validirana prije/poslije prijedloga.

Korektivni prompt za nevaljani citat generira aplikacija i sadrži samo popis citata koji nisu pronađeni.
Model mora vratiti cijelu procjenu ponovno; parcijalno krpanje odgovora nije dopušteno.

## Promptovi treće iteracije

- `profile` sada prima korisnički brief i mora mu dati prednost.
- `synthesis` mora vratiti sve kodno generirane segment ID-jeve istim redoslijedom i točno četiri
  dimenzije, a svaki rewrite mora imati ugrađenu validaciju.

Objektivne text diagnostics metrike nisu promptni output: računa ih Python i model ih dobiva samo kao
dodatne dokaze. Benchmark također ne koristi model, nego uspoređuje spremljene rezultate s ljudskim
oznakama.
