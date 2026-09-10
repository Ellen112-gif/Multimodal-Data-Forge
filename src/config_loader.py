import yaml


def load_config(path: str) -> dict:

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        config = yaml.safe_load(f)

    return config