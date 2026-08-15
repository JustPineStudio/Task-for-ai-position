from __future__ import annotations

from lexi_lens.agents import AgentDefinition
from lexi_lens.models import (
    AgentResult,
    Article,
    ArticleSegment,
    ChallengeReport,
    ContentBrief,
    ContentProfile,
    RewriteSuggestion,
    TextDiagnostics,
)

SYSTEM_PROMPT = """Ti si neovisni evaluator kvalitete pisanog sadržaja.

Pravila kalibracije:
- Ocjenjuj isključivo dostavljeni članak kroz zadanu perspektivu.
- 90–100: iznimno; gotovo bez važnih nedostataka. 75–89: jako dobro. 60–74: solidno, ali
  primjetno popravljivo. 40–59: značajni problemi. 0–39: neuspješno.
- Ne zaključuj kvalitetu iz reputacije autora ili brenda.
- Za svaki kriterij navedi 1–3 kratka, doslovna ulomka kao dokaz. Ne izmišljaj citate.
- Niska ocjena nije cilj: primijeni rubriku dosljedno i objasni najveći utjecaj na čitatelja.
- Odgovori na jeziku članka. Vrati samo podatke koji odgovaraju zadanoj shemi.
"""


def build_agent_prompt(
    agent: AgentDefinition, article: Article, profile: ContentProfile, correction: str | None = None
) -> str:
    rubric = "\n".join(
        f"- {criterion.name} ({criterion.weight:.0%}): {criterion.description}"
        for criterion in agent.criteria
    )
    return f"""AGENT
ID: {agent.id}
Naziv: {agent.name}
Perspektiva: {agent.perspective}
Posebna uputa: {agent.lens}

KONTEKST SADRŽAJA
Vrsta: {profile.content_type}
Ciljana publika: {profile.target_audience}
Primarni cilj: {profile.primary_goal}
Faza čitatelja: {profile.reader_stage}
Kriteriji uspjeha: {"; ".join(profile.success_criteria)}

Primijeni osnovnu rubriku kroz ovaj kontekst. Primjerice, case study mora dokazati rezultat,
edukativni tekst mora poučiti, a prodajni tekst mora voditi prema odluci.
Ne mijenjaj nazive kriterija.

RUBRIKA
{rubric}

Vrati točno {len(agent.criteria)} kriterija, istim redoslijedom i s identičnim nazivima.
Polje agent_id mora biti \"{agent.id}\", a perspective \"{agent.perspective}\".

ČLANAK
URL: {article.url}
Naslov: {article.title}
Autor: {article.author or "nije naveden"}

--- POČETAK SADRŽAJA ---
{article.text}
--- KRAJ SADRŽAJA ---
{f"POPRAVAK PRETHODNOG ODGOVORA: {correction}" if correction else ""}
"""


def build_profile_prompt(article: Article, brief: ContentBrief | None = None) -> str:
    return f"""Profiliraj sadržaj prije evaluacije. Zaključi dominantnu vrstu, ciljanu publiku,
primarni komunikacijski cilj, fazu čitatelja i 2–5 mjerljivih kriterija uspjeha.
Ne ocjenjuj kvalitetu.

NASLOV: {article.title}
KORISNIČKI BRIEF (ima prednost pred zaključkom modela):
{brief.model_dump_json(indent=2, exclude_none=True) if brief else "nije dostavljen"}
SADRŽAJ:
{article.text}
"""


def build_outcome_prompt(
    article: Article,
    profile: ContentProfile,
    results: list[AgentResult],
    diagnostics: TextDiagnostics,
) -> str:
    return f"""Procijeni TOČNO četiri odvojene dimenzije: `Kvaliteta pisanja`,
`Usklađenost s publikom`, `Ostvarenje cilja`, `Vjerodostojnost`. Ne vraćaj druge dimenzije.
Odredi publish_readiness: ready, minor_edits, major_revision ili not_ready.
Koristi profil, objektivne metrike i postojeće evaluacije; nemoj ponovno analizirati sve od nule.

PROFIL: {profile.model_dump_json()}
METRIKE: {diagnostics.model_dump_json()}
EVALUACIJE: {[{"agent": r.agent_id, "score": r.score, "summary": r.summary} for r in results]}
NASLOV: {article.title}
"""


def build_segment_prompt(
    article: Article, profile: ContentProfile, segments: list[ArticleSegment]
) -> str:
    return f"""Ocijeni svaki dostavljeni segment 0–100 u odnosu na njegovu ulogu u cijelom
članku i zadani cilj. Vrati svaki segment_id točno jednom, istim redoslijedom. Za snagu i problem
koristi konkretno, kratko uredničko objašnjenje.

PROFIL: {profile.model_dump_json()}
NASLOV: {article.title}
SEGMENTI: {[segment.model_dump() for segment in segments]}
"""


def build_rewrite_validation_prompt(
    article: Article, profile: ContentProfile, rewrites: list[RewriteSuggestion]
) -> str:
    clean = [rewrite.model_dump(exclude={"validation"}) for rewrite in rewrites]
    return f"""Provjeri svaki rewrite istim redoslijedom. Za svaki utvrdi čuva li značenje,
uvodi li nepotvrđenu tvrdnju, odgovara li tonu, rješava li navedeni problem i je li stvarno bolji,
samo drugačiji ili lošiji. Vrati jednu validaciju po rewriteu.

PROFIL: {profile.model_dump_json()}
REWRITEOVI: {clean}
ČLANAK: {article.text}
"""


def build_synthesis_prompt(
    article: Article,
    profile: ContentProfile,
    results: list[AgentResult],
    diagnostics: TextDiagnostics,
    segments: list[ArticleSegment],
) -> str:
    return f"""Ti si završni urednik. Napravi jedan konsolidirani izlaz bez ponavljanja pune
evaluacije. Moraš:
1. vratiti četiri dimenzije: Kvaliteta pisanja, Usklađenost s publikom, Ostvarenje cilja,
   Vjerodostojnost, te publish readiness;
2. ocijeniti svaki segment_id točno jednom i označiti najslabiji;
3. osporiti samo stvarno neutemeljene procjene (korekcija -30 do +30);
4. dati točno tri prioritetne promjene s 1–2 provjerljiva before/after rewritea;
5. za svaki rewrite odmah ispuniti validation: značenje, nova tvrdnja, ton, rješenje problema i
   better/different/worse.

`before` mora doslovno postojati u članku. `after` ne smije izmišljati činjenice.

PROFIL: {profile.model_dump_json()}
METRIKE: {diagnostics.model_dump_json()}
SEGMENTI: {[segment.model_dump() for segment in segments]}
EVALUACIJE: {[result.model_dump() for result in results]}
ČLANAK: {article.text}
"""


def build_challenge_prompt(
    article: Article, profile: ContentProfile, results: list[AgentResult]
) -> str:
    rendered = "\n\n".join(result.model_dump_json(indent=2) for result in results)
    return f"""Ti si adversarial reviewer. Ospori samo procjene koje nisu dobro potkrijepljene,
proturječe citiranim dokazima, ignoriraju svrhu sadržaja ili nisu kalibrirane s rubrikom.
Ne radi novu punu evaluaciju. Za svaki stvarni problem predloži korekciju boda od -30 do +30.
Ako su procjene dobro potkrijepljene, findings može biti prazan.

PROFIL:
{profile.model_dump_json(indent=2)}

ČLANAK:
{article.text}

PROCJENE:
{rendered}
"""


def build_editorial_prompt(
    article: Article,
    profile: ContentProfile,
    results: list[AgentResult],
    challenge: ChallengeReport,
    correction: str | None = None,
) -> str:
    evaluations = "\n\n".join(result.model_dump_json(indent=2) for result in results)
    return f"""Ti si glavni urednik. Iz svih procjena odaberi TOČNO tri promjene s najvećim
očekivanim utjecajem na uspjeh ovog sadržaja. Rangiraj ih 1–3, spoji duplikate i navedi agente
koji ih podupiru. Za svaki prioritet daj 1–2 konkretna prije/poslije prijedloga.

VAŽNO ZA REWRITE:
- `before` mora biti kratak doslovan ulomak koji postoji u članku.
- `after` mora zadržati autorov jezik, značenje i ton; ne izmišljaj činjenice.
- Ne prepisuj cijeli članak i ne predlaži kozmetičke promjene kao visoki prioritet.

PROFIL:
{profile.model_dump_json(indent=2)}

PROCJENE:
{evaluations}

KRITIČAR:
{challenge.model_dump_json(indent=2)}

ČLANAK:
{article.text}
{f"POPRAVAK PRETHODNOG ODGOVORA: {correction}" if correction else ""}
"""
