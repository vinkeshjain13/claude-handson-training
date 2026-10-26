from pydantic import BaseModel, Field
from typing import Literal

class ExceptionTriage(BaseModel):
    transaction_id: str
    classification: Literal['AMOUNT_MISMATCH','MISSING_SETTLEMENT','MISSING_LEDGER','DUPLICATE_TRANSACTION','DATE_MISMATCH']
    possible_causes: list[str] = Field(min_length=1,max_length=5)
    recommended_action: str = Field(min_length=5)
    requires_human_review: bool = True
    missing_evidence: list[str] = Field(default_factory=list)
