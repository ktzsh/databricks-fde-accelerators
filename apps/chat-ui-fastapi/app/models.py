from pydantic import BaseModel
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

# Data classes for in-memory storage
@dataclass
class Chat:
    id: int
    title: str
    user_id: str
    user_email: str
    user_name: str
    created_at: datetime
    updated_at: datetime
    
    def __init__(self, id: int, title: str, user_id: str, user_email: str, user_name: str):
        self.id = id
        self.title = title
        self.user_id = user_id
        self.user_email = user_email
        self.user_name = user_name
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

@dataclass
class ChatMessage:
    id: int
    chat_id: int
    content: str
    role: str
    created_at: datetime
    attachments: List['MessageAttachment']
    
    def __init__(self, id: int, chat_id: int, content: str, role: str):
        self.id = id
        self.chat_id = chat_id
        self.content = content
        self.role = role
        self.created_at = datetime.utcnow()
        self.attachments = []

@dataclass
class MessageAttachment:
    id: int
    message_id: int
    filename: str
    stored_filename: str  # The actual filename stored on disk
    file_path: str
    file_type: str
    
    def __init__(self, id: int, message_id: int, filename: str, stored_filename: str, file_path: str, file_type: str):
        self.id = id
        self.message_id = message_id
        self.filename = filename
        self.stored_filename = stored_filename
        self.file_path = file_path
        self.file_type = file_type

# Chat schemas
class ChatBase(BaseModel):
    title: str

class ChatCreate(ChatBase):
    pass

class ChatResponse(ChatBase):
    id: int
    user_id: str
    user_email: str
    user_name: str
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

# Message schemas
class MessageBase(BaseModel):
    content: str
    role: str

class MessageCreate(MessageBase):
    chat_id: int
    attachments: Optional[List[str]] = []

class MessageAttachmentResponse(BaseModel):
    id: int
    filename: str
    stored_filename: str
    file_type: str
    
    class Config:
        from_attributes = True

class MessageResponse(MessageBase):
    id: int
    chat_id: int
    created_at: datetime
    attachments: List[MessageAttachmentResponse] = []
    
    class Config:
        from_attributes = True

# Chat with messages
class ChatWithMessages(ChatResponse):
    messages: List[MessageResponse] = []

# User schemas
class UserInfoResponse(BaseModel):
    user_id: str
    email: str
    name: str
    
    class Config:
        from_attributes = True
