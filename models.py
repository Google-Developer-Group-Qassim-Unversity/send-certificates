from pydantic import BaseModel, EmailStr, HttpUrl, model_validator
from datetime import date


class recipeintData(BaseModel):
    email: EmailStr
    name: str

class BaseEventData(BaseModel):
    event_name: str
    announced_event_name: str | None = None
    start_date: date
    end_date: date
    official: bool

class sendBulkEmailData(BaseEventData):
    recipient_google_sheet_url: HttpUrl | None = None
    recipient_uploaded_file_name: str | None = None
    recipient_data: list[recipeintData] | None = None

    @model_validator(mode='after')
    def check_recipient_source(cls, model):
        sheet_set = model.recipient_google_sheet_url is not None
        file_set = model.recipient_uploaded_file_name is not None
        data_set = model.recipient_data is not None
        if (sheet_set + file_set + data_set) > 1:
            raise ValueError("Only one of recipient_google_sheet_url, recipient_uploaded_file_name, or recipient_data should be set.")
        if not sheet_set and not file_set and not data_set:
            raise ValueError("One of recipient_google_sheet_url, recipient_uploaded_file_name, or recipient_data must be set.")
        
        return model

    class Config:
        populate_by_name = True
    
class sendEmailData(BaseEventData):
    recipient_email: EmailStr

    class Config:
        populate_by_name = True