"""What a mushroom picker knows: where and when each mushroom grows — the data of the score.

Only data, no code: the formula is scoring.py. Every number is a factor from 0 (never) to 1
(its favourite); a stand's score for a mushroom is the product of its factors, so one zero
(the wrong tree, the wrong month) rules the stand out.

Where it comes from — checked 4.10.2026:
- The facts — which trees, which forests and soils, which months, young or old stands — follow
  the species' pages of the Polish Wikipedia (Borowik szlachetny, Podgrzybek brunatny, Pieprznik
  jadalny, Koźlarz babka, Maślak zwyczajny, Mleczaj rydz) and of the atlas grzyby.pl (its public
  parts); the kurka and the koźlarz czerwony also English Wikipedia (Cantharellus cibarius,
  Leccinum aurantiacum), Frontiers in Microbiology 2023 (Cantharellus mycorrhiza), the Wageningen
  study of chanterelles and soil acidity, and wildfooduk.com (aspen bolete).
- The numbers are not from any source — nobody publishes such factors. They put those
  descriptions on a scale, and the walks of stage 2 (TODO.md) are what corrects them.
"""

from grzyby_server.miejsca.model import Grzyb, Miesiac, ProfilGrzyba

# BDL's codes of the dominant species → (name, adjective for the stand's name). A suffix after a
# dot is the subspecies (BRZ.O — downy birch), scored as the species (scoring.species).
DRZEWA: dict[str, tuple[str, str]] = {
    "SO": ("sosna", "sosnowy"),
    "ŚW": ("świerk", "świerkowy"),
    "BK": ("buk", "bukowy"),
    "DB": ("dąb", "dębowy"),
    "BRZ": ("brzoza", "brzozowy"),
    "MD": ("modrzew", "modrzewiowy"),
    "OS": ("osika", "osikowy"),
    "GB": ("grab", "grabowy"),
    "LP": ("lipa", "lipowy"),
    "OL": ("olsza", "olszowy"),
    "JS": ("jesion", "jesionowy"),
    "KL": ("klon", "klonowy"),
    "JD": ("jodła", "jodłowy"),
}
INNE_DRZEWO = ("inne drzewo", "mieszany")

# Forest site types → (group, description). Groups are what a picker tells apart; each mushroom
# has a factor per group.
GRUPY_SIEDLISK: dict[str, str] = {
    "bory_swieze": "bory świeże",
    "bory_suche": "bory suche",
    "lasy_swieze": "lasy świeże",
    "wilgotne": "wilgotne",
    "bagienne": "bagienne",
    "olsy_legi": "olsy i łęgi",
}
SIEDLISKA: dict[str, tuple[str, str]] = {
    "BŚW": ("bory_swieze", "bór świeży"),
    "BMŚW": ("bory_swieze", "bór mieszany świeży"),
    "BS": ("bory_suche", "bór suchy"),
    "LMŚW": ("lasy_swieze", "las mieszany świeży"),
    "LŚW": ("lasy_swieze", "las świeży"),
    "BW": ("wilgotne", "bór wilgotny"),
    "BMW": ("wilgotne", "bór mieszany wilgotny"),
    "LMW": ("wilgotne", "las mieszany wilgotny"),
    "LW": ("wilgotne", "las wilgotny"),
    "BB": ("bagienne", "bór bagienny"),
    "BMB": ("bagienne", "bór mieszany bagienny"),
    "LMB": ("bagienne", "las mieszany bagienny"),
    "OL": ("olsy_legi", "ols"),
    "OLJ": ("olsy_legi", "ols jesionowy"),
    "LŁ": ("olsy_legi", "las łęgowy"),
}
# An unknown site type is half as good as the mushroom's best; an unknown tree, not its tree.
NIEZNANE_SIEDLISKO = 0.5

# Age of the dominant species → (below this many years, name); the last class has no bound.
KLASY_WIEKU: list[tuple[int | None, str]] = [
    (20, "młodnik"),
    (40, "młody drzewostan"),
    (121, "dojrzały drzewostan"),
    (None, "stary drzewostan"),
]

# Seasons list only the months a mushroom grows in; a month left out counts as zero.
M = Miesiac
PROFILE: dict[Grzyb, ProfilGrzyba] = {
    Grzyb.BOROWIK: ProfilGrzyba(
        nazwa="borowik",
        dopelniacz="borowika",
        drzewa={"ŚW": 1.0, "SO": 0.9, "BK": 0.9, "DB": 0.9, "JD": 0.8, "BRZ": 0.6, "GB": 0.3},
        siedliska={"bory_swieze": 1.0, "lasy_swieze": 0.9, "bory_suche": 0.5, "wilgotne": 0.5, "bagienne": 0.1, "olsy_legi": 0.05},
        # Most abundant in medium-aged stands, rarer in old coniferous forests (Wikipedia).
        wiek=(0.05, 0.7, 1.0, 0.6),
        sezon={M.MAJ: 0.2, M.CZERWIEC: 0.3, M.LIPIEC: 0.6, M.SIERPIEN: 1, M.WRZESIEN: 1, M.PAZDZIERNIK: 0.6, M.LISTOPAD: 0.15},
    ),
    Grzyb.PODGRZYBEK: ProfilGrzyba(
        nazwa="podgrzybek",
        dopelniacz="podgrzybka",
        drzewa={"SO": 1.0, "ŚW": 0.9, "JD": 0.7, "BK": 0.5, "DB": 0.5, "BRZ": 0.4, "MD": 0.4},
        siedliska={"bory_swieze": 1.0, "bory_suche": 0.7, "lasy_swieze": 0.6, "wilgotne": 0.5, "bagienne": 0.2, "olsy_legi": 0.05},
        wiek=(0.2, 0.8, 1.0, 0.8),
        sezon={M.LIPIEC: 0.3, M.SIERPIEN: 0.7, M.WRZESIEN: 1, M.PAZDZIERNIK: 1, M.LISTOPAD: 0.5, M.GRUDZIEN: 0.1},
    ),
    Grzyb.KURKA: ProfilGrzyba(
        nazwa="kurka",
        dopelniacz="kurki",
        # Oak, pine, spruce, and birch in mycorrhiza experiments (Frontiers 2023); beech from a
        # picker's knowledge only. Acid soils but not below pH 4 (Wageningen), moist moss.
        drzewa={"SO": 1.0, "ŚW": 0.9, "DB": 0.8, "BRZ": 0.7, "BK": 0.7, "JD": 0.6, "GB": 0.4},
        siedliska={"bory_swieze": 1.0, "lasy_swieze": 0.8, "wilgotne": 0.7, "bory_suche": 0.6, "bagienne": 0.2, "olsy_legi": 0.05},
        wiek=(0.2, 0.9, 1.0, 0.8),
        # June to December, picked from late summer to late autumn (Wikipedia); July to October in
        # north-west Russia.
        sezon={M.CZERWIEC: 0.4, M.LIPIEC: 1, M.SIERPIEN: 1, M.WRZESIEN: 0.8, M.PAZDZIERNIK: 0.5, M.LISTOPAD: 0.1},
    ),
    Grzyb.KOZLARZ: ProfilGrzyba(
        nazwa="koźlarz",
        dopelniacz="koźlarza",
        # Koźlarz babka grows only under birches (Wikipedia). Koźlarz czerwony is two species to a
        # picker: the aspen one (L. albostipitatum, aspens and poplars, August to November) and
        # the oak one (L. aurantiacum, oaks and other broadleaves, never conifers). A small factor
        # for conifers stands for birches mixed into a pine or spruce stand.
        drzewa={"BRZ": 1.0, "OS": 0.9, "DB": 0.5, "GB": 0.3, "BK": 0.2, "LP": 0.2, "OL": 0.2, "SO": 0.2, "ŚW": 0.2},
        siedliska={"wilgotne": 1.0, "lasy_swieze": 0.8, "bagienne": 0.7, "bory_swieze": 0.6, "olsy_legi": 0.4, "bory_suche": 0.3},
        wiek=(0.6, 1.0, 0.8, 0.5),
        sezon={M.CZERWIEC: 0.4, M.LIPIEC: 0.8, M.SIERPIEN: 1, M.WRZESIEN: 1, M.PAZDZIERNIK: 0.6, M.LISTOPAD: 0.1},
    ),
    Grzyb.MASLAK: ProfilGrzyba(
        nazwa="maślak",
        dopelniacz="maślaka",
        drzewa={"SO": 1.0, "MD": 1.0, "ŚW": 0.2},
        siedliska={"bory_suche": 1.0, "bory_swieze": 0.9, "lasy_swieze": 0.4, "wilgotne": 0.3, "bagienne": 0.1, "olsy_legi": 0},
        # "Often in young pine plantations" (Wikipedia); from May to autumn.
        wiek=(1.0, 0.8, 0.3, 0.1),
        sezon={
            M.MAJ: 0.1,
            M.CZERWIEC: 0.1,
            M.LIPIEC: 0.3,
            M.SIERPIEN: 0.7,
            M.WRZESIEN: 1,
            M.PAZDZIERNIK: 1,
            M.LISTOPAD: 0.5,
            M.GRUDZIEN: 0.05,
        },
    ),
    Grzyb.RYDZ: ProfilGrzyba(
        nazwa="rydz",
        dopelniacz="rydza",
        # Mleczaj rydz grows with pines only; the spruce is for rydz świerkowy (L. deterrimus,
        # grzyby.pl), which the group includes.
        drzewa={"SO": 1.0, "ŚW": 0.8},
        siedliska={"bory_swieze": 0.9, "bory_suche": 0.8, "lasy_swieze": 0.6, "wilgotne": 0.4, "bagienne": 0.1, "olsy_legi": 0},
        wiek=(1.0, 0.8, 0.3, 0.1),
        sezon={M.SIERPIEN: 0.5, M.WRZESIEN: 1, M.PAZDZIERNIK: 1, M.LISTOPAD: 0.3},
    ),
}
