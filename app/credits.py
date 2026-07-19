from fastapi import HTTPException

from app.auth import get_session
from app.database import get_db, update_session_credits


class CreditService:
    @staticmethod
    def require_credits(session_id: str, amount: int = 10) -> None:
        """Check balance and raise 402 if insufficient. No side effects.

        Call this **before** the paid operation to fail fast when the user
        cannot afford it. After the operation succeeds, call
        ``spend_credits`` to actually deduct.
        """
        session = get_session(session_id)
        with get_db() as conn:
            row = conn.execute(
                "SELECT credits_balance FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        current = row["credits_balance"] if row else session.get("credits_balance", 150)
        if current < amount:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. You have {current}, need {amount}",
            )

    @staticmethod
    def spend_credits(session_id: str, amount: int = 10) -> int:
        """Deduct credits after a successful paid operation.

        Call this **after** the paid operation completes. The balance check
        should already have passed via ``require_credits``.
        """
        session = get_session(session_id)
        with get_db() as conn:
            row = conn.execute(
                "SELECT credits_balance FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        current = row["credits_balance"] if row else session.get("credits_balance", 150)
        new_balance = current - amount
        if row:
            update_session_credits(session_id, new_balance)
        session["credits_balance"] = new_balance
        return new_balance

    @staticmethod
    def deduct_credits(session_id: str, amount: int = 10) -> int:
        """Check balance and deduct in one call (legacy, prefer two-phase).

        Prefer the two-phase ``require_credits`` + ``spend_credits`` pattern
        so credits are only spent after the paid operation succeeds.
        """
        CreditService.require_credits(session_id, amount)
        return CreditService.spend_credits(session_id, amount)

    @staticmethod
    def get_balance(session_id: str) -> int:
        session = get_session(session_id)
        with get_db() as conn:
            row = conn.execute(
                "SELECT credits_balance FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row:
            balance = row["credits_balance"]
            session["credits_balance"] = balance
            return balance
        return session.get("credits_balance", 150)

    @staticmethod
    def add_credits(session_id: str, amount: int) -> int:
        if amount <= 0:
            raise HTTPException(
                status_code=400, detail="Credit top-up amount must be positive"
            )

        session = get_session(session_id)
        current = CreditService.get_balance(session_id)
        new_balance = current + amount
        update_session_credits(session_id, new_balance)
        session["credits_balance"] = new_balance
        return new_balance
