import pandas as pd

from src.data.player_ids import display_name


def test_display_name_formats_and_indexes_by_id():
    df = pd.DataFrame({
        "key_mlbam": [663656, 608369],
        "name_first": ["kyle", "corey"],
        "name_last": ["tucker", "seager"],
    })
    names = display_name(df)

    assert names.loc[663656] == "Tucker, Kyle"
    assert names.loc[608369] == "Seager, Corey"
    assert names.index.name is None or names.index.tolist() == [663656, 608369]


def test_cache_file_exists_and_has_crosswalk_keys():
    """The cached register must carry the keys needed for future joins."""
    from src.data.player_ids import _cache_file

    path = _cache_file()
    assert path.exists(), "run load_player_ids once to populate the cache"

    df = pd.read_csv(path)
    for col in ["key_mlbam", "key_retro", "key_bbref", "key_fangraphs"]:
        assert col in df.columns
