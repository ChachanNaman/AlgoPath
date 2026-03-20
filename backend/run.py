from __future__ import annotations

from app import create_app


app = create_app()


if __name__ == "__main__":
    # Uses `backend/.env` via config.py -> flask env vars.
    app.run(host="0.0.0.0", port=5000, debug=True)


# Test:
# 1) Start MongoDB (Atlas or local) and Redis.
# 2) Install requirements: pip install -r requirements.txt
# 3) Run: python run.py
# 4) Then run curl register/login/me from README.md.

