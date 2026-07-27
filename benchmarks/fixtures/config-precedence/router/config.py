from collections.abc import Mapping


def resolve(*layers: Mapping[str, object]) -> dict[str, object]:
    result: dict[str, object] = {}
    for layer in layers:
        result.update(layer)
    return result


def effective_config() -> dict[str, object]:
    defaults = {"model": "gpt-5.6-terra", "effort": "low", "hooks": False}
    user = {"model": "gpt-5.6-sol", "effort": "high", "hooks": True}
    project = {"model": "gpt-5.6-sol"}
    task = {"effort": "medium"}
    return resolve(defaults, user, project, task)
