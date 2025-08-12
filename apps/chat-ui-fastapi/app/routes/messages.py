from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from typing import List, Optional
import os
import aiofiles
import uuid
from datetime import datetime
from mlflow.deployments import get_deploy_client

from ..database import get_db, Store
from ..models import MessageCreate, MessageResponse, MessageAttachmentResponse
from ..utils import get_current_user_from_headers, get_agent_name, get_env_variable

router = APIRouter(prefix="/messages", tags=["messages"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=MessageResponse)
async def create_message(
    content: str = Form(...),
    chat_id: int = Form(...),
    role: str = Form("user"),
    files: Optional[List[UploadFile]] = File(None),
    request: Request = None,
    store: Store = Depends(get_db)
):
    current_user = get_current_user_from_headers(request)
    
    # Verify chat belongs to user
    chat = store.get_chat(chat_id)
    
    if not chat or chat.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Create message
    message = store.create_message(
        chat_id=chat_id,
        content=content,
        role=role
    )
    
    # Handle file uploads
    if files:
        for file in files:
            if file.filename:
                # Generate unique filename
                file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
                unique_filename = f"{uuid.uuid4()}.{file_extension}"
                file_path = os.path.join(UPLOAD_DIR, unique_filename)
                
                # Save file
                async with aiofiles.open(file_path, 'wb') as f:
                    content_file = await file.read()
                    await f.write(content_file)
                
                # Determine file type
                file_type = "image" if file.content_type and file.content_type.startswith('image/') else "text"
                
                # Create attachment record
                store.create_attachment(
                    message_id=message.id,
                    filename=file.filename,
                    stored_filename=unique_filename,
                    file_path=file_path,
                    file_type=file_type
                )
    
    # Convert to response format
    attachment_responses = []
    for attachment in message.attachments:
        attachment_responses.append(MessageAttachmentResponse(
            id=attachment.id,
            filename=attachment.filename,
            stored_filename=attachment.stored_filename,
            file_type=attachment.file_type
        ))
    
    return MessageResponse(
        id=message.id,
        chat_id=message.chat_id,
        content=message.content,
        role=message.role,
        created_at=message.created_at,
        attachments=attachment_responses
    )

@router.get("/chat/{chat_id}", response_model=List[MessageResponse])
def get_chat_messages(
    chat_id: int,
    request: Request,
    store: Store = Depends(get_db)
):
    current_user = get_current_user_from_headers(request)
    
    # Verify chat belongs to user
    chat = store.get_chat(chat_id)
    
    if not chat or chat.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    messages = store.get_chat_messages(chat_id)
    
    # Convert to response format
    message_responses = []
    for message in messages:
        attachment_responses = []
        for attachment in message.attachments:
            attachment_responses.append(MessageAttachmentResponse(
                id=attachment.id,
                filename=attachment.filename,
                stored_filename=attachment.stored_filename,
                file_type=attachment.file_type
            ))
        
        message_responses.append(MessageResponse(
            id=message.id,
            chat_id=message.chat_id,
            content=message.content,
            role=message.role,
            created_at=message.created_at,
            attachments=attachment_responses
        ))
    
    return message_responses

@router.post("/assistant-response")
async def create_assistant_response(
    chat_id: int = Form(...),
    user_message: str = Form(...),
    request: Request = None,
    store: Store = Depends(get_db)
):
    """
    Create an assistant response to a user message.
    In a real implementation, this would call the Databricks API.
    """
    current_user = get_current_user_from_headers(request)
    
    # Verify chat belongs to user
    chat = store.get_chat(chat_id)
    
    if not chat or chat.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Get agent name from environment variables
    agent_name = get_agent_name()
    
    # Get all user messages
    messages = store.get_chat_messages(chat_id)
  
    # Prepare messages for the API call
    api_messages = []
    for i, msg in enumerate(messages):
        if i == len(messages) - 1:
            # TODO Parse and add attachment to message
            # Last message, include attachments
            if msg.attachments:
                for attachment in msg.attachments:
                    if attachment.file_type == "image":
                        pass
                    elif attachment.file_type == "pdf":
                        pass
                    else:
                        pass

        api_messages.append({
            "role": msg.role,
            "content": msg.content
        })

    # Prepare payload for Databricks serving endpoint
    payload = {
        "messages": api_messages
    }

    # Get endpoint name from environment variables
    endpoint_name = get_env_variable("LLM_SERVING_ENDPOINT", "")

    try:
        # Call Databricks serving endpoint
        if not endpoint_name:
            assistant_content = f"Echo: I'm {agent_name}, this is localhost and I understand you said: '{user_message}'"
        else:
            client = get_deploy_client("databricks")
            response = client.predict(endpoint=endpoint_name, inputs=payload)
            
            # Extract assistant content from response
            # Adjust this based on your endpoint's response format
            if isinstance(response, dict) and "choices" in response:
                assistant_content = response["choices"][0]["message"]["content"]
            elif isinstance(response, dict) and "content" in response:
                assistant_content = response["content"]
            elif isinstance(response, str):
                assistant_content = response
            else:
                # Fallback if response format is unexpected
                assistant_content = str(response)
            
    except Exception as e:
        # Log the error and provide a fallback response
        print(f"Error calling Databricks endpoint: {str(e)}")
        assistant_content = f"I'm experiencing technical difficulties right now, but I'm here to help. Could you please try again?"
    
    # Create assistant message
    message = store.create_message(
        chat_id=chat_id,
        content=assistant_content,
        role="assistant"
    )
    
    # Convert to response format
    attachment_responses = []
    for attachment in message.attachments:
        attachment_responses.append(MessageAttachmentResponse(
            id=attachment.id,
            filename=attachment.filename,
            stored_filename=attachment.stored_filename,
            file_type=attachment.file_type
        ))
    
    return MessageResponse(
        id=message.id,
        chat_id=message.chat_id,
        content=message.content,
        role=message.role,
        created_at=message.created_at,
        attachments=attachment_responses
    )
