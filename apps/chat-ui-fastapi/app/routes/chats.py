from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Optional
from datetime import datetime

from ..database import get_db, Store
from ..models import ChatCreate, ChatResponse, ChatWithMessages, MessageResponse, MessageAttachmentResponse
from ..utils import get_current_user_from_headers

router = APIRouter(prefix="/chats", tags=["chats"])

@router.post("/", response_model=ChatResponse)
def create_chat(
    chat: ChatCreate,
    request: Request,
    store: Store = Depends(get_db)
):
    current_user = get_current_user_from_headers(request)
    
    db_chat = store.create_chat(
        title=chat.title,
        user_id=current_user.user_id,
        user_email=current_user.email,
        user_name=current_user.name
    )
    
    # Convert to response format
    return ChatResponse(
        id=db_chat.id,
        title=db_chat.title,
        user_id=db_chat.user_id,
        user_email=db_chat.user_email,
        user_name=db_chat.user_name,
        created_at=db_chat.created_at,
        updated_at=db_chat.updated_at,
        message_count=0
    )

@router.get("/", response_model=List[ChatResponse])
def get_user_chats(
    request: Request,
    store: Store = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    current_user = get_current_user_from_headers(request)
    
    db_chats = store.get_user_chats(current_user.user_id, skip, limit)
    
    # Convert to response format
    chat_responses = []
    for db_chat in db_chats:
        message_count = store.get_chat_message_count(db_chat.id)
        chat_responses.append(ChatResponse(
            id=db_chat.id,
            title=db_chat.title,
            user_id=db_chat.user_id,
            user_email=db_chat.user_email,
            user_name=db_chat.user_name,
            created_at=db_chat.created_at,
            updated_at=db_chat.updated_at,
            message_count=message_count
        ))
    
    return chat_responses

@router.get("/{chat_id}", response_model=ChatWithMessages)
def get_chat(
    chat_id: int,
    request: Request,
    store: Store = Depends(get_db)
):
    current_user = get_current_user_from_headers(request)
    
    db_chat = store.get_chat(chat_id)
    
    if not db_chat or db_chat.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Get messages for this chat
    chat_messages = store.get_chat_messages(chat_id)
    
    # Convert messages to response format
    message_responses = []
    for chat_message in chat_messages:
        attachment_responses = []
        for attachment in chat_message.attachments:
            attachment_responses.append(MessageAttachmentResponse(
                id=attachment.id,
                filename=attachment.filename,
                stored_filename=attachment.stored_filename,
                file_type=attachment.file_type
            ))
        
        message_responses.append(MessageResponse(
            id=chat_message.id,
            chat_id=chat_message.chat_id,
            content=chat_message.content,
            role=chat_message.role,
            created_at=chat_message.created_at,
            attachments=attachment_responses
        ))
    
    return ChatWithMessages(
        id=db_chat.id,
        title=db_chat.title,
        user_id=db_chat.user_id,
        user_email=db_chat.user_email,
        user_name=db_chat.user_name,
        created_at=db_chat.created_at,
        updated_at=db_chat.updated_at,
        message_count=len(message_responses),
        messages=message_responses
    )

@router.put("/{chat_id}", response_model=ChatResponse)
def update_chat(
    chat_id: int,
    chat_update: ChatCreate,
    request: Request,
    store: Store = Depends(get_db)
):
    current_user = get_current_user_from_headers(request)
    
    db_chat = store.get_chat(chat_id)
    
    if not db_chat or db_chat.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    updated_chat = store.update_chat(chat_id, chat_update.title)
    
    if not updated_chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    message_count = store.get_chat_message_count(chat_id)
    
    return ChatResponse(
        id=updated_chat.id,
        title=updated_chat.title,
        user_id=updated_chat.user_id,
        user_email=updated_chat.user_email,
        user_name=updated_chat.user_name,
        created_at=updated_chat.created_at,
        updated_at=updated_chat.updated_at,
        message_count=message_count
    )

@router.delete("/{chat_id}")
def delete_chat(
    chat_id: int,
    request: Request,
    store: Store = Depends(get_db)
):
    current_user = get_current_user_from_headers(request)
    
    db_chat = store.get_chat(chat_id)
    
    if not db_chat or db_chat.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    success = store.delete_chat(chat_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    return {"message": "Chat deleted successfully"}
