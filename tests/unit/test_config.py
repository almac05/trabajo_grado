from proyecto_grado.etl import config


def test_inicializar_entorno_carga_env_una_sola_vez_y_crea_directorios(monkeypatch):
    env_calls = []
    mkdir_calls = []

    monkeypatch.setattr(config, "_ENV_LOADED", False)

    def fake_load_dotenv(path, *args, **kwargs):
        env_calls.append(path)
        return True

    monkeypatch.setattr(config, "load_dotenv", fake_load_dotenv)
    monkeypatch.setattr(
        config.os,
        "makedirs",
        lambda path, exist_ok=False: mkdir_calls.append((path, exist_ok)),
    )

    result = config.inicializar_entorno(verbose=False)
    config.inicializar_entorno(verbose=False)

    assert env_calls == [config.PROJECT_ROOT / ".env"]
    assert len(mkdir_calls) == len(config._directorios_salida()) * 2
    assert all(exist_ok for _, exist_ok in mkdir_calls)
    assert result["PROJECT_ROOT"] == config.PROJECT_ROOT
