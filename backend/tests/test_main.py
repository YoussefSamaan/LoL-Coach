from app import main


class TestMain:
    def test_health_check_root(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "service": "lol-coach-backend"}

    def test_health_check_v1(self, client):
        r = client.get("/v1/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_version(self, client):
        r = client.get("/version")
        assert r.status_code == 200
        assert r.json() == {"version": "0.1.0"}

    def test_openapi_contains_v1_routes(self, client):
        """
        Ensures the v1 router is actually mounted.
        """
        r = client.get("/openapi.json")
        assert r.status_code == 200

        schema = r.json()
        assert "/health" in schema["paths"]
        assert "/v1/health" in schema["paths"]
        assert any(path.startswith("/v1/") for path in schema["paths"])

    def test_openapi_metadata(self, client):
        """
        Guards against accidental API metadata regressions.
        """
        r = client.get("/openapi.json")
        schema = r.json()

        assert schema["info"]["title"] == "LoL Coach Draft Assistant"
        assert schema["info"]["version"] == "0.1.0"

    def test_run_uses_default_env(self, monkeypatch):
        calls = {}

        def fake_run(app_str, host, port, reload):
            calls["app_str"] = app_str
            calls["host"] = host
            calls["port"] = port
            calls["reload"] = reload

        # Patch uvicorn.run that is imported inside main.run()
        monkeypatch.setattr("uvicorn.run", fake_run, raising=True)

        # Ensure env vars are not set
        monkeypatch.delenv("PORT", raising=False)
        monkeypatch.delenv("RELOAD", raising=False)

        main.run()

        assert calls == {
            "app_str": "app.main:app",
            "host": "0.0.0.0",
            "port": 8000,
            "reload": True,
        }

    def test_run_reads_env_vars(self, monkeypatch):
        calls = {}

        def fake_run(app_str, host, port, reload):
            calls["app_str"] = app_str
            calls["host"] = host
            calls["port"] = port
            calls["reload"] = reload

        monkeypatch.setattr("uvicorn.run", fake_run, raising=True)

        monkeypatch.setenv("PORT", "1234")
        monkeypatch.setenv("RELOAD", "false")

        main.run()

        assert calls["port"] == 1234
        assert calls["reload"] is False
