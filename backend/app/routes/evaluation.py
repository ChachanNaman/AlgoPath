from __future__ import annotations

from flask import Blueprint, jsonify, request


evaluation_bp = Blueprint("evaluation_bp", __name__)


@evaluation_bp.post("/")
def evaluate_placeholder():
    # Phase 4 will implement full hybrid scoring logic here or inside quiz submit route.
    _ = request.get_json(silent=True) or {}
    return jsonify({"message": "Not implemented yet (Phase 4 evaluation)."}), 501


# Test:
# curl -X POST http://localhost:5000/api/evaluation/ \
#   -H "Content-Type: application/json" \
#   -H "Authorization: Bearer TOKEN_HERE" \
#   -d '{}'

