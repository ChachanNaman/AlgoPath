from __future__ import annotations

from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.recommendation_service import compute_recommendations


recommendations_bp = Blueprint("recommendations_bp", __name__)


@recommendations_bp.get("/<user_id>")
@jwt_required()
def get_recommendations(user_id: str):
    # Security: only allow fetching for the authenticated user.
    identity = get_jwt_identity()
    if str(identity) != str(user_id):
        return jsonify({"message": "forbidden"}), 403

    db = current_app.config["MONGO_DB"]
    payload = compute_recommendations(user_id, db)
    return jsonify(payload), 200


# Test:
# curl http://localhost:5000/api/recommendations/arjun@test.com \
#   -H "Authorization: Bearer TOKEN_HERE"

