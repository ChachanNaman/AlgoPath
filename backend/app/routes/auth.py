from __future__ import annotations

import re
from datetime import datetime

import bcrypt
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from pymongo.errors import PyMongoError


auth_bp = Blueprint("auth_bp", __name__)


def _clean_text(value: str, max_len: int = 2000) -> str:
    # Minimal sanitization for any user-supplied strings used in prompts later.
    value = (value or "").strip()[:max_len]
    # Strip HTML tags (best-effort).
    value = re.sub(r"<[^>]*?>", "", value)
    return value


def _user_public(user_doc: dict) -> dict:
    user_doc = dict(user_doc)
    user_doc["_id"] = str(user_doc.get("_id"))
    user_doc.pop("password_hash", None)
    return user_doc


@auth_bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    name = _clean_text(payload.get("name", ""))
    email = _clean_text(payload.get("email", "").lower())
    password = payload.get("password", "")

    if not name or not email or not password:
        return jsonify({"message": "name, email, and password are required"}), 400

    if len(password) < 6:
        return jsonify({"message": "password must be at least 6 characters"}), 400

    users = current_app.config["MONGO_DB"]["users"]
    try:
        existing = users.find_one({"email": email})
    except PyMongoError:
        return jsonify({"message": "database unavailable; check MongoDB Atlas network/TLS settings"}), 503
    if existing:
        return jsonify({"message": "email already exists"}), 409

    salt = bcrypt.gensalt(rounds=12)
    password_hash = bcrypt.hashpw(password.encode("utf-8"), salt)

    now = datetime.utcnow()
    try:
        users.insert_one(
            {
                "name": name,
                "email": email,
                "password_hash": password_hash,
                "created_at": now,
                "language_pref": "en",
                "streak_days": 0,
                # MongoDB/BSON cannot encode Python `datetime.date` objects reliably.
                # Store as a proper UTC datetime instead.
                "last_active": now,
            }
        )
    except PyMongoError:
        return jsonify({"message": "database unavailable; check MongoDB Atlas network/TLS settings"}), 503

    # Return token immediately after register
    token = create_access_token(identity=email)
    user_doc = users.find_one({"email": email})
    return jsonify({"token": token, "user": _user_public(user_doc)}), 201


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = _clean_text(payload.get("email", "").lower())
    password = payload.get("password", "")

    if not email or not password:
        return jsonify({"message": "email and password are required"}), 400

    users = current_app.config["MONGO_DB"]["users"]
    try:
        user_doc = users.find_one({"email": email})
    except PyMongoError:
        return jsonify({"message": "database unavailable; check MongoDB Atlas network/TLS settings"}), 503
    if not user_doc:
        return jsonify({"message": "invalid credentials"}), 401

    stored_hash = user_doc.get("password_hash")
    if not stored_hash or not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
        return jsonify({"message": "invalid credentials"}), 401

    try:
        users.update_one({"_id": user_doc["_id"]}, {"$set": {"last_active": datetime.utcnow()}})
    except PyMongoError:
        return jsonify({"message": "database unavailable; check MongoDB Atlas network/TLS settings"}), 503

    token = create_access_token(identity=email)
    user_doc = users.find_one({"email": email})
    return jsonify({"token": token, "user": _user_public(user_doc)}), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    identity = get_jwt_identity()
    users = current_app.config["MONGO_DB"]["users"]
    user_doc = users.find_one({"email": identity})
    if not user_doc:
        return jsonify({"message": "user not found"}), 404
    return jsonify({"user": _user_public(user_doc)}), 200


# Test (Phase 1):
# 1) Register:
# curl -X POST http://localhost:5000/api/auth/register \
#   -H "Content-Type: application/json" \
#   -d '{"name":"Test","email":"test@example.com","password":"test123"}'
# 2) Login:
# curl -X POST http://localhost:5000/api/auth/login \
#   -H "Content-Type: application/json" \
#   -d '{"email":"test@example.com","password":"test123"}'
# 3) Me:
# curl http://localhost:5000/api/auth/me -H "Authorization: Bearer TOKEN_HERE"
#
# Quick verification for this bugfix:
# - Run register curl (from your terminal).
# - It should no longer crash with:
#   `bson.errors.InvalidDocument: cannot encode object: datetime.date(...)`

