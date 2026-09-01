import json

from fastapi import APIRouter, HTTPException, status

from app.database import connection, encode_json
from app.schemas import Profile, ProfileInput

router = APIRouter(prefix="/profiles", tags=["profiles"])


def row_to_profile(row: object) -> Profile:
    values = dict(row)  # type: ignore[arg-type]
    return Profile(
        id=values["id"], user_id=values["user_id"], risk_profile=values["risk_profile"],
        investment_horizon_years=values["investment_horizon_years"], maximum_volatility=values["maximum_volatility"],
        portfolio=json.loads(values["portfolio_json"]), watchlist=json.loads(values["watchlist_json"]),
        interaction_history=json.loads(values["interaction_history_json"]),
        created_at=values["created_at"], updated_at=values["updated_at"],
    )


@router.post("", response_model=Profile, status_code=status.HTTP_201_CREATED)
def upsert_profile(payload: ProfileInput) -> Profile:
    with connection() as conn:
        conn.execute("""
          INSERT INTO user_profiles (user_id,risk_profile,investment_horizon_years,maximum_volatility,portfolio_json,watchlist_json,interaction_history_json)
          VALUES (?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
          risk_profile=excluded.risk_profile, investment_horizon_years=excluded.investment_horizon_years,
          maximum_volatility=excluded.maximum_volatility, portfolio_json=excluded.portfolio_json,
          watchlist_json=excluded.watchlist_json, interaction_history_json=excluded.interaction_history_json,
          updated_at=CURRENT_TIMESTAMP
        """, (payload.user_id, payload.risk_profile, payload.investment_horizon_years, payload.maximum_volatility,
               encode_json(payload.portfolio), encode_json(payload.watchlist), encode_json(payload.interaction_history)))
        row = conn.execute("SELECT * FROM user_profiles WHERE user_id=?", (payload.user_id,)).fetchone()
    return row_to_profile(row)


@router.get("/{user_id}", response_model=Profile)
def get_profile(user_id: str) -> Profile:
    with connection() as conn:
        row = conn.execute("SELECT * FROM user_profiles WHERE user_id=?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return row_to_profile(row)

