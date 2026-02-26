"""Mail API schemas."""

from pydantic import BaseModel, Field


class EmailAddress(BaseModel):
    name: str | None = None
    email: str


class Mailbox(BaseModel):
    id: str
    name: str
    role: str | None = None  # inbox, sent, drafts, trash, junk, archive
    unread_count: int = 0
    total_count: int = 0
    sort_order: int = 0


class MailboxListResponse(BaseModel):
    mailboxes: list[Mailbox]


class Attachment(BaseModel):
    blob_id: str
    name: str | None = None
    type: str | None = None
    size: int = 0


class MessageSummary(BaseModel):
    id: str
    thread_id: str | None = None
    mailbox_ids: list[str] = []
    from_: list[EmailAddress] = []
    to: list[EmailAddress] = []
    subject: str | None = None
    preview: str | None = None
    received_at: str | None = None
    is_unread: bool = False
    is_flagged: bool = False
    has_attachment: bool = False

    model_config = {"populate_by_name": True}


class MessageListResponse(BaseModel):
    messages: list[MessageSummary]
    total: int = 0
    page: int = 0
    limit: int = 50


class MessageDetail(BaseModel):
    id: str
    thread_id: str | None = None
    mailbox_ids: list[str] = []
    from_: list[EmailAddress] = []
    to: list[EmailAddress] = []
    cc: list[EmailAddress] = []
    bcc: list[EmailAddress] = []
    reply_to: list[EmailAddress] = []
    subject: str | None = None
    text_body: str | None = None
    html_body: str | None = None
    preview: str | None = None
    received_at: str | None = None
    is_unread: bool = False
    is_flagged: bool = False
    attachments: list[Attachment] = []

    model_config = {"populate_by_name": True}


class MessageUpdateRequest(BaseModel):
    is_unread: bool | None = None
    is_flagged: bool | None = None
    mailbox_ids: list[str] | None = None  # move to mailbox


class SendMessageRequest(BaseModel):
    account_id: str | None = None  # which account to send from
    to: list[EmailAddress]
    cc: list[EmailAddress] = []
    bcc: list[EmailAddress] = []
    subject: str = ""
    text_body: str = ""
    html_body: str | None = None
    in_reply_to: str | None = None  # message id for threading
    references: list[str] = []


class BulkActionRequest(BaseModel):
    account_id: str | None = None
    message_ids: list[str]
    action: str  # "read", "unread", "star", "unstar", "delete", "move"
    mailbox_id: str | None = None  # target mailbox for "move"


class SignatureCreate(BaseModel):
    name: str = Field(..., max_length=100)
    html_content: str = Field(..., max_length=50000)
    is_default: bool = False


class SignatureUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    html_content: str | None = Field(None, max_length=50000)
    is_default: bool | None = None


class SignatureResponse(BaseModel):
    id: str
    name: str
    html_content: str
    is_default: bool
    created_at: str

    model_config = {"from_attributes": True}


# ─── Mail Account schemas ───


class MailAccountCreate(BaseModel):
    display_name: str = Field(..., max_length=100)
    email: str = Field(..., max_length=255)
    imap_host: str = Field(..., max_length=255)
    imap_port: int = 993
    imap_security: str = "ssl"
    smtp_host: str = Field(..., max_length=255)
    smtp_port: int = 587
    smtp_security: str = "starttls"
    username: str = Field(..., max_length=255)
    password: str = Field(..., max_length=500)
    is_default: bool = False


class MailAccountUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=100)
    email: str | None = Field(None, max_length=255)
    imap_host: str | None = Field(None, max_length=255)
    imap_port: int | None = None
    imap_security: str | None = None
    smtp_host: str | None = Field(None, max_length=255)
    smtp_port: int | None = None
    smtp_security: str | None = None
    username: str | None = Field(None, max_length=255)
    password: str | None = Field(None, max_length=500)
    is_default: bool | None = None


class MailAccountResponse(BaseModel):
    id: str
    display_name: str
    email: str
    imap_host: str
    imap_port: int
    imap_security: str
    smtp_host: str
    smtp_port: int
    smtp_security: str
    username: str
    is_default: bool
    last_sync_at: str | None = None
    sync_error: str | None = None
