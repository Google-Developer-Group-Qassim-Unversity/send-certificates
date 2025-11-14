import aiosmtplib
from email.message import EmailMessage
from fastapi import FastAPI, HTTPException
from edit_pptx import replace_placeholder, pptx_to_pdf
from models import sendBulkEmailData
from pydantic import BaseModel, HttpUrl
from pathlib import Path
import pandas as pd
from pydantic import EmailStr, ValidationError
from dotenv import load_dotenv
from os import getenv
import asyncio
load_dotenv()

app = FastAPI()

SENDER_EMAIL = "albrrak773@gmail.com"

@app.get("/")
async def root():
    return {"message": "Welcome to the Email Sending API"}


@app.post("/email/bulk")
async def send_bulk_email(body: sendBulkEmailData):
    try:
        # Extract recipient data
        if body.recipient_google_sheet_url:
            data = extract_data(sheets_link=body.recipient_google_sheet_url)
            print(f"Extracted {len(data)} recipients from Google Sheets.")
        else:
            data = extract_data(uploaded_file_name=body.recipient_uploaded_file_name)
            print(f"Extracted {len(data)} recipients from uploaded file.")
        print(f"Preparing to send emails to {len(data)} recipients.")
        # Single SMTP session for all emails
        sent_emails = []
        tasks = []
        for index, (email, name) in enumerate(data):
            print(f"{'-'*10}\n[{index+1}] Sending email for {email}\n{'-'*10}")
            # Create simple email message
            message = EmailMessage()
            message["From"] = SENDER_EMAIL
            message["To"] = email
            message["Subject"] = f"[{index+1}] Test Email"
            message.set_content(f"Hello {name}, this is a test email.")
            
            task = send_email(message)
            print(f"Created task")
            tasks.append(task)
            sent_emails.append(email)
        
        # Wait for all emails to be sent
        await asyncio.gather(*tasks, return_exceptions=True)
            
        
        return {
            "message": f"Successfully sent {len(sent_emails)} emails",
            "sent_to": sent_emails
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending emails: {str(e)}")


def extract_data(sheets_link: HttpUrl | None = None, uploaded_file_name: str | None = None):
    # 1. Load data from Google Sheets or uploaded file
    if sheets_link:
        df = pd.read_csv(sheets_link.__str__())
    elif uploaded_file_name:
        df = pd.read_excel(uploaded_file_name)
    else:
        raise ValueError("Either sheets_link or uploaded_file_name must be provided.")

    # 2. Validate required columns
    df.columns = df.columns.str.strip()
    required_columns = ['email', 'name']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
        
    # 3. validate non-empty cells in required columns
    for col in required_columns:
        if df[col].isnull().any():
            null_rows = df[df[col].isnull()].index.tolist()
            null_rows = [row_index + 2 for row_index in null_rows]  # +2 for header and 0-based index
            print(f"Column '{col}' has empty cells at rows: {null_rows}")

    # 4. validate emails
    class emailCheck(BaseModel):
        email: EmailStr

    # 4.1 check for duplicate emails
    dups = df[df["email"].duplicated(keep=False)].index.tolist()
    if dups:
        dups = [i+2 for i in dups]
        print(f"Duplicate emails found at rows: {dups}")

    # 4.2 check for invalid email formats
    invalid_index = []
    for index, email in df['email'].items():
        try:
            emailCheck(email=email)
        except ValidationError as e:
            invalid_index.append(index + 2)
    if invalid_index:
        print(f"Invalid emails found at rows: {invalid_index}")

    # 5. Strip values and return list of tuples (email, name)
    result = []
    for _, row in df.iterrows():
        email = str(row['email']).strip()
        name = str(row['name']).strip()
        result.append((email, name))
    return result

async def send_email(message):
    print(f"Sending email to \x1b[32m{message['To']}\x1b[0m...")
    # Create task for sending email
    print(f"Creating SMTP client for...")
    smtp = aiosmtplib.SMTP(
        hostname="smtp.gmail.com",
        port=587, 
        start_tls=True, 
        username=SENDER_EMAIL, 
        password=getenv("APP_PASSWORD")
    )
    print(f"SMTP client created.")
    print("Connecting to SMTP server...")
    await smtp.connect()
    print("Connected to SMTP server.")
    await smtp.send_message(message)
    print(f"Email sent to \x1b[32m{message['To']}\x1b[0m successfully ✅")
# if __name__ == "__main__":
#     extract_data(uploaded_file_name=Path("./recipt.xlsx"))