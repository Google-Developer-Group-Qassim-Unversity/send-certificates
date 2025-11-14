from pydantic import BaseModel, EmailStr, HttpUrl, model_validator
from datetime import date


class sendBulkEmailData(BaseModel):
    event_name: str
    announced_event_name: str | None = None
    start_date: date
    end_date: date
    official: bool
    recipient_google_sheet_url: HttpUrl | None = None
    recipient_uploaded_file_name: str | None = None

    @model_validator(mode='after')
    def check_recipient_source(cls, model):
        sheet_set = model.recipient_google_sheet_url is not None
        file_set = model.recipient_uploaded_file_name is not None
        if sheet_set and file_set:
            raise ValueError("Only one of recipient_google_sheet_url or recipient_uploaded_file_name should be set.")
        if not sheet_set and not file_set:
            raise ValueError("One of recipient_google_sheet_url or recipient_uploaded_file_name must be set.")
        return model

    class Config:
        populate_by_name = True
    
class sendEmailData(BaseModel):
    event_name: str
    announced_event_name: str | None = None
    start_date: date
    end_date: date
    official: bool
    recipient_email: EmailStr

    class Config:
        populate_by_name = True