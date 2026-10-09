from beranda.providers import photos


def test_no_folder_is_empty():
    assert photos.list_photos("") == []
    assert photos.list_photos("/no/such/folder") == []


def test_lists_only_pictures(tmp_path):
    (tmp_path / "beach.jpg").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("not a picture")
    (tmp_path / "logo.png").write_bytes(b"x")
    names = photos.list_photos(str(tmp_path))
    assert set(names) == {"beach.jpg", "logo.png"}


def test_newest_first(tmp_path):
    import os
    import time

    old = tmp_path / "old.jpg"
    old.write_bytes(b"x")
    time.sleep(0.01)
    new = tmp_path / "new.jpg"
    new.write_bytes(b"x")
    os.utime(new, None)
    assert photos.list_photos(str(tmp_path))[0] == "new.jpg"


def test_resolve_rejects_escape_and_unknown(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"x")
    secret = tmp_path.parent / "secret.txt"
    secret.write_text("nope")
    assert photos.resolve(str(tmp_path), "a.jpg") == tmp_path / "a.jpg"
    assert photos.resolve(str(tmp_path), "../secret.txt") is None
    assert photos.resolve(str(tmp_path), "missing.jpg") is None
    assert photos.resolve(str(tmp_path), "a.jpg/../../secret.txt") is None
    assert photos.resolve("", "a.jpg") is None
