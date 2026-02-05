"""
Утилита для парсинга метрик Prometheus из текстового формата.
"""

import re
from typing import Any


def parse_metrics(metrics_text: str) -> dict[str, Any]:
    """
    Парсит метрики Prometheus из текстового формата.

    Args:
        metrics_text: Текст метрик в формате Prometheus

    Returns:
        Словарь вида:
        {
            "metric_name": {
                "type": "counter|gauge|histogram",
                "values": [
                    {"labels": {"label1": "value1"}, "value": 123.45},
                    {"labels": {}, "value": 67.89}
                ]
            }
        }
    """
    metrics: dict[str, Any] = {}
    current_metric = None
    current_type = None

    for raw_line in metrics_text.split("\n"):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            if line.startswith("# TYPE"):
                parts = line.split()
                if len(parts) >= 3:
                    current_metric = parts[2]
                    current_type = parts[3] if len(parts) > 3 else "unknown"
                    if current_metric not in metrics:
                        metrics[current_metric] = {"type": current_type, "values": []}
            continue

        if "{" in line:
            match = re.match(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)\{([^}]+)\}\s+([0-9.eE+-]+)", line)
            if match:
                metric_name = match.group(1)
                labels_str = match.group(2)
                value = float(match.group(3))

                labels = {}
                for label_pair in labels_str.split(","):
                    if "=" in label_pair:
                        key, val = label_pair.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip('"')
                        labels[key] = val

                if metric_name not in metrics:
                    metrics[metric_name] = {"type": "unknown", "values": []}

                metrics[metric_name]["values"].append({"labels": labels, "value": value})
        else:
            match = re.match(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)\s+([0-9.eE+-]+)", line)
            if match:
                metric_name = match.group(1)
                value = float(match.group(2))

                if metric_name not in metrics:
                    metrics[metric_name] = {"type": "unknown", "values": []}

                metrics[metric_name]["values"].append({"labels": {}, "value": value})

    return metrics


def get_metric_value(metrics: dict[str, Any], metric_name: str, labels: dict[str, str] | None = None) -> float | None:
    """
    Получить значение метрики.

    Args:
        metrics: Словарь метрик из parse_metrics()
        metric_name: Имя метрики
        labels: Лейблы для поиска (если None, возвращает первое значение без лейблов или сумму всех)

    Returns:
        Значение метрики или None, если не найдена
    """
    if metric_name not in metrics:
        return None

    metric_data = metrics[metric_name]

    if labels is None:
        values_without_labels = [v["value"] for v in metric_data["values"] if not v["labels"]]
        if values_without_labels:
            return values_without_labels[0]
        return sum(v["value"] for v in metric_data["values"])

    for value_data in metric_data["values"]:
        if value_data["labels"] == labels:
            return value_data["value"]

    return None


def get_metric_sum(metrics: dict[str, Any], metric_name: str, labels_filter: dict[str, str] | None = None) -> float:
    """
    Получить сумму всех значений метрики (с учетом фильтра по лейблам).

    Args:
        metrics: Словарь метрик из parse_metrics()
        metric_name: Имя метрики
        labels_filter: Фильтр по лейблам (если None, суммирует все значения)

    Returns:
        Сумма значений метрики
    """
    if metric_name not in metrics:
        return 0.0

    metric_data = metrics[metric_name]

    if labels_filter is None:
        return sum(v["value"] for v in metric_data["values"])

    total = 0.0
    for value_data in metric_data["values"]:
        if all(value_data["labels"].get(k) == v for k, v in labels_filter.items()):
            total += value_data["value"]

    return total
