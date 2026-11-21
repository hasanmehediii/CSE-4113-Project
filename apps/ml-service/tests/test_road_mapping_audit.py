import copy

import pytest

from app.audit_road_mapping import audit, load, main, same_place


@pytest.fixture(scope="module")
def supplied():
    return load()


def test_supplied_mapping_has_no_structural_errors(supplied):
    report = audit(*supplied)
    assert report["errors"] == []
    assert report["dataset_segments"] == 210
    assert report["mapped_segments"] + report["unmapped_segments"] == 210
    assert report["mapped_corridors"] == report["map_corridors"] == len(supplied[2])
    assert sum(report["unmapped_by_dataset_road"].values()) == report["unmapped_segments"]
    assert main([]) == 0


def test_structural_errors_are_reported(supplied):
    segments, mapping, catalog = supplied
    broken = copy.deepcopy(mapping)
    first, second = list(broken)[:2]
    broken[second].append(broken[first][0])        # shared by two corridors
    broken[first].append("DHK999A")                # unknown, and only one direction
    broken.pop(list(broken)[-1])                   # catalog corridor without mapping
    errors = audit(segments, broken, catalog)["errors"]
    assert any("mapped 2 times" in e for e in errors)
    assert any("DHK999A: unknown segment ID" in e for e in errors)
    assert any("DHK999 is mapped in one direction only" in e for e in errors)
    assert any("catalog road has no mapped segments" in e for e in errors)


def test_endpoint_mismatch_is_flagged_for_review(supplied):
    segments, mapping, catalog = supplied
    catalog = copy.deepcopy(catalog)
    road = next(r for r in catalog if r["id"] == "dhaka-gulshan")
    road["from"], road["to"] = "Mohakhali", "Tejgaon"
    row = next(r for r in audit(segments, mapping, catalog)["corridors"] if r["road_id"] == "dhaka-gulshan")
    assert any("endpoints differ" in note for note in row["review"])


@pytest.mark.parametrize("a, b, same", [
    ("Shahbagh", "Shahbag", True), ("Kuril", "Kuril Bishwa Road", True),
    ("Khamar Bari junction", "Khamarbari", True), ("Dhanmondi south", "Dhanmondi 27", False),
    ("", "Farmgate", False),
])
def test_place_names_tolerate_spelling_variants(a, b, same):
    assert same_place(a, b) is same
