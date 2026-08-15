from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Criterion:
    name: str
    description: str
    weight: float


@dataclass(frozen=True)
class AgentDefinition:
    id: str
    name: str
    perspective: str
    weight: float
    criteria: tuple[Criterion, ...]
    lens: str


AGENTS: tuple[AgentDefinition, ...] = (
    AgentDefinition(
        id="structure",
        name="Arhitekt teksta",
        perspective="Struktura i tok",
        weight=0.30,
        lens=(
            "Procijeni put čitatelja: obećanje naslova i uvoda, redoslijed ideja, prijelaze, "
            "hijerarhiju naslova i završetak. Ne nagrađuj samu prisutnost podnaslova "
            "ako tok nije logičan."
        ),
        criteria=(
            Criterion(
                "Obećanje i fokus", "Tekst rano postavlja temu i ispunjava obećanje naslova.", 0.30
            ),
            Criterion(
                "Logičan tok", "Ideje se nadograđuju bez skokova, ponavljanja i digresija.", 0.35
            ),
            Criterion("Skenabilnost", "Naslovi, odlomci i liste pomažu brzom razumijevanju.", 0.20),
            Criterion("Završetak", "Zaključak sintetizira vrijednost i zatvara narativ.", 0.15),
        ),
    ),
    AgentDefinition(
        id="psychology",
        name="Psiholog čitatelja",
        perspective="Pažnja, motivacija i povjerenje",
        weight=0.25,
        lens=(
            "Promatraj tekst iz perspektive stvarnog čitatelja. Procijeni konkretnost, "
            "relevantnu korist, kognitivno opterećenje, emocionalne okidače i ljudski ton. "
            "Razlikuj uvjeravanje od manipulacije."
        ),
        criteria=(
            Criterion(
                "Relevantnost i benefit",
                "Čitatelju je jasno zašto mu sadržaj vrijedi vremena.",
                0.30,
            ),
            Criterion(
                "Konkretnost",
                "Apstraktne tvrdnje poduprte su primjerima, slikama ili situacijama.",
                0.25,
            ),
            Criterion(
                "Pažnja i ritam",
                "Otvaranje, varijacija i napetost održavaju pažnju bez trikova.",
                0.25,
            ),
            Criterion(
                "Ton i empatija", "Glas je ljudski, primjeren publici i poštuje čitatelja.", 0.20
            ),
        ),
    ),
    AgentDefinition(
        id="clarity",
        name="Urednik jasnoće",
        perspective="Jasnoća i stil",
        weight=0.25,
        lens=(
            "Uredi strogo, ali ne kažnjavaj namjernu osobnost. Traži precizne riječi, "
            "ekonomične rečenice, dosljedan registar i lako razumljive veze među tvrdnjama."
        ),
        criteria=(
            Criterion("Razumljivost", "Rečenice i pojmovi razumljivi su ciljanoj publici.", 0.30),
            Criterion(
                "Sažetost", "Svaki odlomak napreduje; višak i ponavljanje su ograničeni.", 0.25
            ),
            Criterion(
                "Preciznost",
                "Tvrdnje i formulacije su specifične, nedvosmislene i gramatične.",
                0.25,
            ),
            Criterion("Glas i dosljednost", "Stil, obraćanje i ton ostaju koherentni.", 0.20),
        ),
    ),
    AgentDefinition(
        id="credibility",
        name="Skeptični strateg",
        perspective="Vjerodostojnost i korisnost",
        weight=0.20,
        lens=(
            "Provjeri koliko tekst zaslužuje povjerenje i može li čitatelj nešto napraviti "
            "s njime. Ocjenjuj samo ono što je u članku; ne provjeravaj činjenice izvan "
            "dostavljenog sadržaja."
        ),
        criteria=(
            Criterion(
                "Potpora tvrdnjama",
                "Važne tvrdnje imaju izvor, objašnjenje ili uvjerljiv primjer.",
                0.35,
            ),
            Criterion(
                "Nijanse i integritet", "Tekst priznaje granice i ne pretjeruje radi efekta.", 0.20
            ),
            Criterion(
                "Praktična vrijednost",
                "Čitatelj dobiva primjenjive uvide ili sljedeće korake.",
                0.30,
            ),
            Criterion(
                "Usklađenost obećanja", "Naslov, uvod i sadržaj isporučuju istu vrijednost.", 0.15
            ),
        ),
    ),
)
