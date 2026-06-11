"""测试懂球帝球员综合能力数据解析"""

from app.services.dongqiudi_player_ability import parse_ability_payload


def test_parse_ability_payload_extracts_overall_and_radar():
    """测试解析综合能力和雷达图6项数据"""
    payload = {
        "data": {
            "average": {"val": 91, "lv": "lv_1"},
            "redar": [
                {"name": "速度", "val": 88},
                {"name": "力量", "val": 88},
                {"name": "防守", "val": 47},
                {"name": "盘带", "val": 80},
                {"name": "传球", "val": 71},
                {"name": "射门", "val": 92},
            ],
            "star_bar": [
                {"name": "国际声望", "val": 5},
                {"name": "逆足能力", "val": 3},
                {"name": "花式技巧", "val": 3},
            ],
            "foot_info": {"name": "惯用脚", "val": "L"},
            "good_pos": {"name": "注册位置", "val": "ST"},
            "version": "FC 26",
            "last_grab_time": "2026-06-09 12:23:28",
            "bar_info": [],
            "fields": [],
        },
        "errmsg": "success",
        "errno": 0,
    }

    result = parse_ability_payload(payload, ability_id="259656")

    assert result["ability_id"] == "259656"
    assert result["overall"] == 91
    assert result["pace"] == 88
    assert result["shooting"] == 92
    assert result["passing"] == 71
    assert result["dribbling"] == 80
    assert result["defending"] == 47
    assert result["physical"] == 88
    assert result["foot"] == "L"
    assert result["registered_position"] == "ST"
    assert result["version"] == "FC 26"
    assert result["last_grab_time"] == "2026-06-09 12:23:28"


def test_parse_ability_payload_star_skills():
    """测试解析星级技能"""
    payload = {
        "data": {
            "average": {"val": 85},
            "redar": [],
            "star_bar": [
                {"name": "国际声望", "val": 4},
                {"name": "逆足能力", "val": 5},
                {"name": "花式技巧", "val": 2},
            ],
            "foot_info": {"name": "惯用脚", "val": "R"},
            "good_pos": {"name": "注册位置", "val": "CF"},
            "version": "FC 26",
            "last_grab_time": "2026-06-09 12:00:00",
            "bar_info": [],
            "fields": [],
        },
        "errmsg": "success",
        "errno": 0,
    }

    result = parse_ability_payload(payload, ability_id="100001")

    assert result["star_skills"] is not None
    skills = result["star_skills"]  # JSON字符串或dict
    if isinstance(skills, str):
        import json
        skills = json.loads(skills)

    assert skills[0]["name"] == "国际声望"
    assert skills[0]["val"] == 4
    assert skills[1]["name"] == "逆足能力"
    assert skills[1]["val"] == 5
    assert skills[2]["name"] == "花式技巧"
    assert skills[2]["val"] == 2


def test_parse_ability_payload_bar_info():
    """测试解析bar_info（7大类详细能力）"""
    payload = {
        "data": {
            "average": {"val": 91},
            "redar": [],
            "star_bar": [],
            "foot_info": {"name": "惯用脚", "val": "L"},
            "good_pos": {"name": "注册位置", "val": "ST"},
            "version": "FC 26",
            "last_grab_time": "2026-06-09 12:23:28",
            "bar_info": [
                {
                    "title": "进攻",
                    "detail": [
                        {"name": "传中", "val": 58},
                        {"name": "射门", "val": 96},
                    ],
                    "total": 154,
                },
                {
                    "title": "力量",
                    "detail": [
                        {"name": "射门力量", "val": 94},
                        {"name": "强壮", "val": 93},
                    ],
                    "total": 187,
                },
            ],
            "fields": [],
        },
        "errmsg": "success",
        "errno": 0,
    }

    result = parse_ability_payload(payload, ability_id="259656")

    assert result["bar_info"] is not None
    bar_info = result["bar_info"]
    if isinstance(bar_info, str):
        import json
        bar_info = json.loads(bar_info)

    assert len(bar_info) == 2
    assert bar_info[0]["title"] == "进攻"
    assert bar_info[0]["detail"][0]["name"] == "传中"
    assert bar_info[0]["detail"][0]["val"] == 58


def test_parse_ability_payload_position_ratings():
    """测试解析各位置评分"""
    payload = {
        "data": {
            "average": {"val": 91},
            "redar": [],
            "star_bar": [],
            "foot_info": {"name": "惯用脚", "val": "L"},
            "good_pos": {"name": "注册位置", "val": "ST"},
            "version": "FC 26",
            "last_grab_time": "2026-06-09 12:23:28",
            "bar_info": [],
            "fields": [
                {"name": "中锋", "val": 93},
                {"name": "右边锋", "val": 82},
                {"name": "前腰", "val": 86},
            ],
        },
        "errmsg": "success",
        "errno": 0,
    }

    result = parse_ability_payload(payload, ability_id="259656")

    assert result["position_ratings"] is not None
    ratings = result["position_ratings"]
    if isinstance(ratings, str):
        import json
        ratings = json.loads(ratings)

    assert len(ratings) == 3
    assert ratings[0]["name"] == "中锋"
    assert ratings[0]["val"] == 93


def test_parse_ability_payload_empty_data():
    """测试API返回空数据时的处理"""
    payload = {"data": None, "errmsg": "not found", "errno": 1001}

    result = parse_ability_payload(payload, ability_id="999999")

    assert result is None


def test_parse_ability_payload_missing_radar_item():
    """测试雷达图缺少某一项时默认值为0"""
    payload = {
        "data": {
            "average": {"val": 85},
            "redar": [
                {"name": "速度", "val": 90},
                # 缺少"力量"
                {"name": "防守", "val": 30},
                {"name": "盘带", "val": 82},
                {"name": "传球", "val": 75},
                {"name": "射门", "val": 88},
            ],
            "star_bar": [],
            "foot_info": {"name": "惯用脚", "val": "R"},
            "good_pos": {"name": "注册位置", "val": "LW"},
            "version": "FC 26",
            "last_grab_time": "2026-06-09 12:00:00",
            "bar_info": [],
            "fields": [],
        },
        "errmsg": "success",
        "errno": 0,
    }

    result = parse_ability_payload(payload, ability_id="100002")

    assert result["pace"] == 90
    assert result["physical"] == 0  # 缺失默认为0
    assert result["shooting"] == 88
