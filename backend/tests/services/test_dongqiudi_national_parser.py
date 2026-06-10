import pytest

from app.services.dongqiudi_national_roster import (
    extract_standings_teams,
    parse_statistics,
    parse_team_members,
    build_profile_url,
)


def test_extract_standings_teams_deduplicates_links():
    html = """
    <table>
      <tr><td><a href="/team/789">法国</a></td></tr>
      <tr><td><a href="/team/269">巴西</a></td></tr>
      <tr><td><a href="/team/789">法国</a></td></tr>
    </table>
    """

    teams = extract_standings_teams(html)

    assert teams == [
        {"dongqiudi_team_id": "789", "name_cn": "法国", "team_url": "https://pc.dongqiudi.com/team/789"},
        {"dongqiudi_team_id": "269", "name_cn": "巴西", "team_url": "https://pc.dongqiudi.com/team/269"},
    ]


def test_parse_statistics_list_to_dict():
    statistic = [{"出场": "8"}, {"进球": "6"}, {"助攻": "3"}, {"身价(欧)": "1.8亿"}]

    assert parse_statistics(statistic) == {
        "出场": "8",
        "进球": "6",
        "助攻": "3",
        "身价(欧)": "1.8亿",
    }


def test_build_profile_url():
    assert build_profile_url("50226848") == "https://pc.dongqiudi.com/player/50226848"
    assert build_profile_url(None) is None


def test_parse_team_members_groups_coaches_and_players():
    payload = {
        "code": 0,
        "message": "",
        "data": {
            "list": [
                {
                    "title": "教练",
                    "type": "coach",
                    "data": [
                        {
                            "person_id": "50070602",
                            "person_name": "德尚",
                            "person_logo": "coach.jpg",
                            "age": "57岁",
                            "nationality_name": "法国",
                            "type": "主教练",
                            "scheme": "dongqiudi:///coach/50070602",
                        }
                    ],
                },
                {
                    "title": "前锋",
                    "type": "attacker",
                    "data": [
                        {
                            "person_id": "50226848",
                            "person_name": "姆巴佩",
                            "person_en_name": "Kylian Mbappé",
                            "person_logo": "mbappe.jpg",
                            "shirtnumber": "10",
                            "age": "27岁",
                            "nationality_name": "皇家马德里",
                            "type": "attacker",
                            "weekly_salary": "35.9",
                            "statistic": [
                                {"出场": "8"},
                                {"进球": "6"},
                                {"助攻": "3"},
                                {"身价(欧)": "1.8亿"},
                            ],
                            "scheme": "dongqiudi:///player/50226848",
                        }
                    ],
                },
            ]
        },
    }

    parsed = parse_team_members("789", payload)

    assert parsed["dongqiudi_team_id"] == "789"
    assert len(parsed["coaches"]) == 1
    assert parsed["coaches"][0]["person_id"] == "50070602"
    assert parsed["coaches"][0]["profile_url"] == "https://pc.dongqiudi.com/player/50070602"
    assert parsed["coaches"][0]["role_type"] == "主教练"

    assert len(parsed["players"]) == 1
    player = parsed["players"][0]
    assert player["person_id"] == "50226848"
    assert player["person_name"] == "姆巴佩"
    assert player["person_en_name"] == "Kylian Mbappé"
    assert player["jersey_number"] == 10
    assert player["club_name_cn"] == "皇家马德里"
    assert player["appearances"] == 8
    assert player["goals"] == 6
    assert player["assists"] == 3
    assert player["market_value_text"] == "1.8亿"
    assert player["profile_url"] == "https://pc.dongqiudi.com/player/50226848"
    assert player["raw_data"]["person_name"] == "姆巴佩"


def test_parse_team_members_rejects_non_zero_code():
    with pytest.raises(RuntimeError):
        parse_team_members("789", {"code": 100, "message": "bad"})
