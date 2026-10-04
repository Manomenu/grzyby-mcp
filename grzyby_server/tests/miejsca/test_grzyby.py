"""The mushroom profiles hold together: every site type has a group, every group a factor for
every mushroom, every mushroom a season. (Their values are checked by pydantic: 0 to 1.)"""

import pytest

from grzyby_server.miejsca import grzyby
from grzyby_server.miejsca.model import Grzyb


def test_every_site_type_belongs_to_a_known_group() -> None:
    assert {group for group, _ in grzyby.SIEDLISKA.values()} == set(grzyby.GRUPY_SIEDLISK)


@pytest.mark.parametrize("g", list(Grzyb))
def test_every_mushroom_has_a_profile_with_every_site_group_and_a_season(g: Grzyb) -> None:
    profile = grzyby.PROFILE[g]

    assert set(profile.siedliska) == set(grzyby.GRUPY_SIEDLISK)
    assert set(profile.drzewa) <= set(grzyby.DRZEWA)
    assert max(profile.sezon.values()) == 1  # each has a peak month
    assert len(profile.wiek) == len(grzyby.KLASY_WIEKU)
