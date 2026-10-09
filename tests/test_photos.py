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


# ---- v0.12: Beranda's own folder, uploads, Dropbox -----------------------------------------
import io
import zipfile

import pytest

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 32
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def test_the_default_folder_comes_from_the_installer_setting(monkeypatch, tmp_path):
    monkeypatch.setenv("BERANDA_PHOTOS", str(tmp_path / "mine"))
    assert photos.default_folder() == tmp_path / "mine"
    assert photos.effective_folder("") == tmp_path / "mine"
    assert photos.effective_folder("   ") == tmp_path / "mine"
    assert photos.effective_folder(str(tmp_path / "other")) == tmp_path / "other"


def test_the_default_folder_without_the_setting_is_under_the_users_home(monkeypatch):
    monkeypatch.delenv("BERANDA_PHOTOS", raising=False)
    assert photos.default_folder().parts[-3:] == ("beranda", "photos") or photos.default_folder().name == "photos"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("IMG_2031.JPG", "IMG_2031.jpg"),
        ("Holiday 1 (best).png", "Holiday-1-best.png"),
        ("../../etc/passwd.jpg", "passwd.jpg"),
        ("C:\\Users\\me\\pic.jpeg", "pic.jpeg"),
        ("été à la mer.webp", "t-la-mer.webp"),
        (".jpg", "photo.jpg"),
    ],
)
def test_file_names_from_a_phone_are_made_safe(raw, expected):
    assert photos.safe_name(raw) == expected


def test_save_stores_a_picture_and_never_overwrites(tmp_path):
    assert photos.save(tmp_path, "a.jpg", JPEG) == "a.jpg"
    assert photos.save(tmp_path, "a.jpg", JPEG) == "a-1.jpg"
    assert photos.save(tmp_path, "a.jpg", JPEG) == "a-2.jpg"
    assert sorted(photos.list_photos(tmp_path)) == ["a-1.jpg", "a-2.jpg", "a.jpg"]


def test_save_checks_the_content_not_just_the_name(tmp_path):
    for name, data, code in [
        ("a.jpg", b"", "bad"),
        ("a.jpg", b"<html>not a picture</html>", "bad"),
        ("a.exe", JPEG, "bad"),
        ("a.png", JPEG[:2], "bad"),
        ("a.jpg", JPEG + b"0" * photos.MAX_UPLOAD_BYTES, "big"),
    ]:
        with pytest.raises(photos.PhotoError) as caught:
            photos.save(tmp_path, name, data)
        assert caught.value.code == code
    assert photos.list_photos(tmp_path) == []


def test_a_picture_cannot_pose_as_a_dropbox_copy(tmp_path):
    assert photos.save(tmp_path, "dropbox-x.jpg", JPEG) == "my-dropbox-x.jpg"


def test_delete_only_removes_pictures_inside_the_folder(tmp_path):
    photos.save(tmp_path, "a.jpg", JPEG)
    outside = tmp_path.parent / "keep.jpg"
    outside.write_bytes(JPEG)
    assert photos.delete(tmp_path, "../keep.jpg") is False and outside.exists()
    assert photos.delete(tmp_path, "missing.jpg") is False
    assert photos.delete(tmp_path, "a.jpg") is True and photos.list_photos(tmp_path) == []


@pytest.mark.parametrize(
    ("link", "expected"),
    [
        ("https://www.dropbox.com/scl/fo/abc/xyz?rlkey=k&dl=0", "https://www.dropbox.com/scl/fo/abc/xyz?rlkey=k&dl=1"),
        ("https://www.dropbox.com/sh/abc/xyz", "https://www.dropbox.com/sh/abc/xyz?dl=1"),
        ("http://dropbox.com/sh/abc/xyz", "https://dropbox.com/sh/abc/xyz?dl=1"),
    ],
)
def test_a_dropbox_share_link_becomes_a_download_link(link, expected):
    assert photos.dropbox_download_url(link) == expected


@pytest.mark.parametrize("link", ["", "https://example.org/sh/abc", "https://notdropbox.com/x", "https://dropbox.com.evil.io/x", "ftp://dropbox.com/x"])
def test_only_real_dropbox_links_are_accepted(link):
    with pytest.raises(photos.PhotoError) as caught:
        photos.dropbox_download_url(link)
    assert caught.value.code == "link"


def _zip(files: dict[str, bytes]) -> io.BytesIO:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    buffer.seek(0)
    return buffer


def test_extracting_a_dropbox_zip_keeps_pictures_only_and_tags_them(tmp_path):
    result = photos.extract_zip(
        _zip({"Trip/a.jpg": JPEG, "Trip/b.png": PNG, "Trip/readme.txt": b"hi", "Trip/fake.jpg": b"not an image"}),
        tmp_path,
    )
    assert result == {"added": 2, "removed": 0, "total": 2}
    assert sorted(photos.list_photos(tmp_path)) == ["dropbox-a.jpg", "dropbox-b.png"]


def test_syncing_again_adds_new_removes_deleted_and_leaves_your_own_uploads_alone(tmp_path):
    photos.save(tmp_path, "mine.jpg", JPEG)
    photos.extract_zip(_zip({"a.jpg": JPEG, "b.png": PNG}), tmp_path)
    result = photos.extract_zip(_zip({"b.png": PNG, "c.jpg": JPEG}), tmp_path)
    assert result == {"added": 1, "removed": 1, "total": 2}
    assert sorted(photos.list_photos(tmp_path)) == ["dropbox-b.png", "dropbox-c.jpg", "mine.jpg"]


def test_a_dropbox_page_instead_of_a_zip_is_explained(tmp_path):
    with pytest.raises(photos.PhotoError) as caught:
        photos.extract_zip(io.BytesIO(b"<html>sign in</html>"), tmp_path)
    assert caught.value.code == "link"
