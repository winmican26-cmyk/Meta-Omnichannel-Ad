import json

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.database import get_db, init_db
from app.schemas.campaign import CampaignCreateRequest


class TemplateRecord(BaseModel):
    id: int
    name: str
    original_adset_id: str | None = None
    created_at: str


class SaveTemplateRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    config: CampaignCreateRequest
    original_adset_id: str | None = None


class DuplicateTemplateRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    new_name: str = Field(..., min_length=1)
    new_daily_budget: int = Field(..., ge=100)


class TemplatesService:
    @staticmethod
    def save_as_template(
        *,
        session_id: str,
        name: str,
        config: CampaignCreateRequest,
        original_adset_id: str | None = None,
    ) -> None:
        init_db()
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO campaign_templates (name, session_id, original_adset_id, config)
                VALUES (?, ?, ?, ?)
                """,
                (
                    name,
                    session_id,
                    original_adset_id,
                    json.dumps(config.model_dump(mode="json")),
                ),
            )
            conn.commit()

    @staticmethod
    def list_templates(
        session_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TemplateRecord]:
        init_db()
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT id, name, original_adset_id, created_at
                FROM campaign_templates
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (session_id, limit, offset),
            ).fetchall()
        return [TemplateRecord(**dict(row)) for row in rows]

    @staticmethod
    def duplicate_from_template(
        *,
        template_id: int,
        session_id: str,
        new_name: str,
        new_daily_budget: int,
    ) -> CampaignCreateRequest:
        init_db()
        with get_db() as conn:
            row = conn.execute(
                "SELECT config FROM campaign_templates WHERE id = ? AND session_id = ?",
                (template_id, session_id),
            ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Template not found")

        config_dict = json.loads(row["config"])
        config_dict["session_id"] = session_id
        config_dict["name"] = new_name
        config_dict["daily_budget"] = new_daily_budget
        return CampaignCreateRequest.model_validate(config_dict)
