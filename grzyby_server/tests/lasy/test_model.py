from grzyby_server.lasy.model import TILE_LAT, TILE_LON, Tile, tiles_around


def test_a_tile_knows_its_box_and_its_id() -> None:
    tile = Tile(541, 152)

    assert tile.id == "541_152"
    assert Tile.parse(tile.id) == tile
    assert tile.bbox == (152 * TILE_LON, 541 * TILE_LAT, 153 * TILE_LON, 542 * TILE_LAT)


def test_a_circle_takes_the_tiles_its_box_touches() -> None:
    # 15 km around Suwałki: about 0.27° of latitude and 0.46° of longitude.
    tiles = tiles_around(54.10, 22.93, 15_000)

    assert len({t.row for t in tiles}) == 4
    assert len({t.col for t in tiles}) == 4
    assert Tile(541, 152) in tiles  # the tile of Suwałki itself


def test_a_small_circle_inside_one_tile_takes_that_tile() -> None:
    assert tiles_around(54.15, 23.02, 500) == [Tile(541, 153)]
