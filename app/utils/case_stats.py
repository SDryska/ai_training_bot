from __future__ import annotations

from app.repositories.case_stats import increment_case_stat


async def mark_case_started(user_id: int, case_id: str) -> None:
    await increment_case_stat(user_id, case_id, "started")


async def mark_case_completed(user_id: int, case_id: str) -> None:
    await increment_case_stat(user_id, case_id, "completed")


async def mark_case_out_of_moves(user_id: int, case_id: str) -> None:
    await increment_case_stat(user_id, case_id, "out_of_moves")


async def mark_case_auto_finished(user_id: int, case_id: str) -> None:
    await increment_case_stat(user_id, case_id, "auto_finished")


