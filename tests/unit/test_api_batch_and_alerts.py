import json


class TestBatchScoring:
    def test_batch_scoring_success(self, api_client):
        payload = {
            "records": [
                {
                    "precipitation": 10,
                    "roll_3d": 20,
                    "roll_7d": 7,
                    "roll_30d": 5,
                    "cumulative": 300,
                    "z_score": 1.2,
                    "location": "Accra",
                },
                {
                    "precipitation": 25,
                    "roll_3d": 50,
                    "roll_7d": 14,
                    "roll_30d": 9,
                    "cumulative": 600,
                    "z_score": 2.5,
                    "location": "Tema",
                },
            ]
        }

        response = api_client.post("/score/batch", json=payload)

        assert response.status_code == 200

        data = response.json()

        assert data["total_records"] == 2
        assert "results" in data
        assert "summary" in data
        assert len(data["results"]) == 2

    def test_batch_empty_records(self, api_client):
        response = api_client.post(
            "/score/batch",
            json={"records": []},
        )

        assert response.status_code == 400
        assert "No records provided" in response.text

    def test_batch_limit_exceeded(self, api_client):
        records = []

        for _ in range(366):
            records.append(
                {
                    "precipitation": 5,
                    "roll_3d": 10,
                    "roll_7d": 4,
                    "roll_30d": 2,
                    "cumulative": 100,
                    "z_score": 0.5,
                }
            )

        response = api_client.post(
            "/score/batch",
            json={"records": records},
        )

        assert response.status_code == 400
        assert "365 records" in response.text

    def test_batch_partial_failure(self, api_client, monkeypatch):
        from src.api import main

        original_score_record = main.score_record

        call_count = {"count": 0}

        def failing_score(record):
            call_count["count"] += 1

            if call_count["count"] == 2:
                raise ValueError("Model failure")

            return original_score_record(record)

        monkeypatch.setattr(main, "score_record", failing_score)

        payload = {
            "records": [
                {
                    "precipitation": 10,
                    "roll_3d": 20,
                    "roll_7d": 7,
                    "roll_30d": 5,
                    "cumulative": 300,
                    "z_score": 1.2,
                },
                {
                    "precipitation": 20,
                    "roll_3d": 40,
                    "roll_7d": 12,
                    "roll_30d": 8,
                    "cumulative": 500,
                    "z_score": 2.0,
                },
            ]
        }

        response = api_client.post("/score/batch", json=payload)

        assert response.status_code == 200

        data = response.json()

        assert len(data["results"]) == 2
        assert "error" in data["results"][1]


class TestAlertsEndpoint:
    def test_get_alerts_when_log_missing(self, api_client, tmp_path, monkeypatch):
        fake_log = tmp_path / "missing.jsonl"

        monkeypatch.setattr("src.api.main.LOG_PATH", fake_log)

        response = api_client.get("/alerts")

        assert response.status_code == 200

        data = response.json()

        assert data["alerts"] == []
        assert data["total"] == 0

    def test_get_alerts_success(self, api_client, tmp_path, monkeypatch):
        fake_log = tmp_path / "alerts.jsonl"

        entries = [
            {
                "location": "Accra",
                "score": 88,
                "risk_tier": "HIGH",
            },
            {
                "location": "Tema",
                "score": 92,
                "risk_tier": "CRITICAL",
            },
        ]

        with open(fake_log, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        monkeypatch.setattr("src.api.main.LOG_PATH", fake_log)

        response = api_client.get("/alerts")

        assert response.status_code == 200

        data = response.json()

        assert data["total"] == 2
        assert len(data["alerts"]) == 2


class TestDistrictsEndpoint:
    def test_districts_endpoint(self, api_client):
        response = api_client.get("/districts")

        assert response.status_code == 200

        data = response.json()

        assert data["city"] == "Accra, Ghana"
        assert "districts" in data
        assert len(data["districts"]) > 0

    def test_district_structure(self, api_client):
        response = api_client.get("/districts")

        data = response.json()

        district = data["districts"][0]

        assert "district" in district
        assert "risk_zone" in district
        assert "elevation_m" in district
