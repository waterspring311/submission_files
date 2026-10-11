from flask import jsonify
from datetime import date, datetime
from decimal import Decimal


def to_jsonable(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def ok(**payload):
    return jsonify(to_jsonable({"ok": True, **payload}))


def created(**payload):
    return ok(**payload), 201


def fail(error, status=400, **payload):
    return jsonify(to_jsonable({"ok": False, "error": error, **payload})), status
