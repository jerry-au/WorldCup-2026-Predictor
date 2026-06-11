from app.services.dongqiudi_player_season_summaries import parse_player_page, parse_statistic_payload


def test_parse_player_page_extracts_season_summary_tabs():
    html = """
    <div class="pp-tabs">
      <button>总计</button><button class="active">联赛</button><button>杯赛</button><button>国家队</button>
    </div>
    <table class="pp-table">
      <thead>
        <tr>
          <th>赛季</th><th>俱乐部</th><th>上场</th><th>首发</th>
          <th>进球</th><th>助攻</th><th>黄牌</th><th>红牌</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>2026</td><td>萧山HD</td><td>14</td><td>11</td>
          <td>5</td><td>3</td><td>3</td><td>0</td>
        </tr>
        <tr>
          <td>2025</td><td>金泉尚武</td><td>34</td><td>30</td>
          <td>13</td><td>11</td><td>1</td><td>0</td>
        </tr>
      </tbody>
    </table>
    """

    records = parse_player_page(html, "50259656")

    assert records == [
        {
            "category": "league",
            "season": "2026",
            "club_name": "萧山HD",
            "appearances": 14,
            "starts": 11,
            "goals": 5,
            "assists": 3,
            "yellow_cards": 3,
            "red_cards": 0,
        },
        {
            "category": "league",
            "season": "2025",
            "club_name": "金泉尚武",
            "appearances": 34,
            "starts": 30,
            "goals": 13,
            "assists": 11,
            "yellow_cards": 1,
            "red_cards": 0,
        },
    ]


def test_parse_statistic_payload_extracts_all_categories():
    payload = {
        "total": [
            {
                "season": {"name": "2025/2026"},
                "team": {"short_name": "曼城"},
                "list": [
                    {"title": "出场", "value": "52"},
                    {"title": "首发", "value": "48"},
                    {"title": "进球", "value": "38"},
                    {"title": "助攻", "value": "9"},
                    {"title": "黄牌", "value": "2"},
                    {"title": "红牌", "value": "0"},
                ],
            }
        ],
        "league": [
            {
                "competition": {"short_name": "英超"},
                "season": {"name": "2025/2026"},
                "team": {"short_name": "曼城"},
                "base_info": {
                    "appearances": "35",
                    "starts": "34",
                    "goals": "27",
                    "assists": "8",
                },
                "discipline": {"yellow_cards": "2", "red_cards": "0"},
            }
        ],
        "cup": [],
        "national": [],
    }

    records = parse_statistic_payload(payload)

    assert records == [
        {
            "category": "total",
            "season": "2025/2026",
            "club_name": "曼城",
            "competition_name": None,
            "appearances": 52,
            "starts": 48,
            "goals": 38,
            "assists": 9,
            "yellow_cards": 2,
            "red_cards": 0,
        },
        {
            "category": "league",
            "season": "2025/2026",
            "club_name": "曼城",
            "competition_name": "英超",
            "appearances": 35,
            "starts": 34,
            "goals": 27,
            "assists": 8,
            "yellow_cards": 2,
            "red_cards": 0,
        },
    ]
