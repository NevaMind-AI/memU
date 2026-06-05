from __future__ import annotations

from memu.utils.dedupe import dedupe_resource_plans


def test_dedupe_resource_plans_removes_duplicate_entries_across_segments() -> None:
    plans = [
        {
            "resource_url": "conversation_#segment_0.json",
            "entries": [
                ("profile", "User likes coffee.", ["preferences"]),
                ("knowledge", "User works in AI.", ["work_life"]),
            ],
        },
        {
            "resource_url": "conversation_#segment_1.json",
            "entries": [
                ("profile", "  user likes   coffee.  ", ["preferences", "habits"]),
                ("event", "User joined a hackathon.", ["experiences"]),
            ],
        },
    ]

    deduped = dedupe_resource_plans(plans)

    assert [entry[1] for plan in deduped for entry in plan["entries"]] == [
        "User likes coffee.",
        "User works in AI.",
        "User joined a hackathon.",
    ]
    assert deduped[0]["entries"][0][2] == ["preferences", "habits"]
    assert deduped[1]["entries"] == [("event", "User joined a hackathon.", ["experiences"])]


def test_dedupe_resource_plans_keeps_same_content_for_different_memory_types() -> None:
    plans = [
        {
            "resource_url": "notes.txt",
            "entries": [
                ("profile", "Uses Python daily.", ["preferences"]),
                ("skill", "Uses Python daily.", ["knowledge"]),
            ],
        }
    ]

    deduped = dedupe_resource_plans(plans)

    assert deduped[0]["entries"] == [
        ("profile", "Uses Python daily.", ["preferences"]),
        ("skill", "Uses Python daily.", ["knowledge"]),
    ]


def test_dedupe_resource_plans_drops_empty_and_malformed_entries() -> None:
    plans = [
        {
            "resource_url": "notes.txt",
            "entries": [
                ("profile", "  ", ["preferences"]),
                ("profile", "Valid memory.", ["preferences", "Preferences", ""]),
                ["profile", "not a tuple", []],
            ],
        }
    ]

    deduped = dedupe_resource_plans(plans)

    assert deduped[0]["entries"] == [("profile", "Valid memory.", ["preferences"])]
