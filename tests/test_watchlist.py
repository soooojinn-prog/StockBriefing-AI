from stockbriefing.watchlist import load_watchlist


def test_load_watchlist_parses_entries(tmp_path):
    f = tmp_path / "wl.yaml"
    f.write_text(
        "stocks:\n  - {code: '005930', name: 삼성전자}\n  - {code: '000660', name: SK하이닉스}\n",
        encoding="utf-8",
    )
    wl = load_watchlist(str(f))
    assert wl == [("005930", "삼성전자"), ("000660", "SK하이닉스")]


def test_load_watchlist_missing_file_returns_empty():
    assert load_watchlist("does/not/exist.yaml") == []
