from griddy.normalize import (
    normalize_live_case,
    normalize_planned_case,
    parse_planned_page,
    planned_page_key,
)

PAGE = """
<table>
  <tr><th><strong>City</strong></th><th><strong>From</strong></th><th><strong>To</strong></th><th>More</th></tr>
  <tr><td>Hal Tarxien </td><td> 27 July 2026 07:00  </td><td> 27 July 2026 12:00 </td><td onclick="x"><i class="fa"></i></td></tr>
  <tr id="row0" style="display:none;"><td colspan="3"> TRIQ SANT&#039; ANTNIN , TRIQ PAOLA   </td><td onclick="y"><i></i></td></tr>
  <tr><td>Paola </td><td> 29 July 2026 07:00  </td><td> 29 July 2026 11:00 </td><td onclick="x"><i></i></td></tr>
  <tr id="row1" style="display:none;"><td colspan="3">Due to scheduled maintenance works on the national electricity grid there may be electricity supply interruptions in (or in parts of) the following areas: ,  TRIQ LAMPUKA , TRIQ L- ORATORJU   </td><td onclick="y"><i></i></td></tr>
</table>
"""


def test_parse_planned_page_rows_and_streets():
    rows = parse_planned_page(PAGE)
    assert len(rows) == 2
    assert rows[0]["city"] == "Hal Tarxien"
    assert rows[0]["from"] == "27 July 2026 07:00"
    assert "TRIQ SANT' ANTNIN" in rows[0]["streets"]
    # boilerplate sentence stripped, streets kept
    assert rows[1]["streets"] == ["TRIQ LAMPUKA", "TRIQ L- ORATORJU"]


def test_planned_page_key_includes_streets():
    rows = parse_planned_page(PAGE)
    # same row -> same key, deterministic
    assert planned_page_key(rows[0]) == planned_page_key(dict(rows[0]))
    # different rows -> different keys
    assert planned_page_key(rows[0]) != planned_page_key(rows[1])
    # two works sharing city and window but differing in streets must NOT collide
    assert planned_page_key(rows[0]) != planned_page_key(dict(rows[0], streets=["different"]))


def test_privacy_fields_are_stripped():
    case = {
        "CaseID": 41008,
        "StartDate": "2026-07-30T08:00:00+02:00",
        "EndDate": "2026-07-30T12:00:00+02:00",
        "InCharge": "SDTO Somebody",
        "AffectedAccountNos": "123456,654321",
        "Transformers": "[{'TransformerId': '866', 'FeederList': [{'FeederNo': '6', 'WKTs': ['LINESTRING (1 2, 3 4)']}]}]",
        "StreetList": "[]",
    }
    norm = normalize_planned_case(case)
    text = str(norm)
    assert "Somebody" not in text
    assert "123456" not in text
    assert norm["CaseID"] == "41008"
    assert norm["transformers"] == [{"TransformerId": "866", "feeders": ["6"]}]
    assert "transformers_sha256" in norm
    # heavy WKT geometry must not be archived
    assert "LINESTRING" not in text


def test_live_case_geometry_hashed_and_privacy_stripped():
    case = {
        "OutageType": 2,
        "X": 54000.1,
        "Y": 71000.2,
        "PolygonGeometry": "1 2, 3 4, 5 6",
        "CentroidGeometry": "3 4",
        "InCharge": "Somebody",
    }
    norm = normalize_live_case(case)
    assert norm["OutageType"] == 2
    assert "InCharge" not in norm
    assert "PolygonGeometry" not in norm
    assert "geometry_sha256" in norm
