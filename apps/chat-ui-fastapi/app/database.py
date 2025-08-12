from datetime import datetime
from typing import Dict, List, Optional
from .models import Chat, ChatMessage, MessageAttachment


class Store:
    def __init__(self):
        self.chats: Dict[int, Chat] = {}
        self.messages: Dict[int, ChatMessage] = {}
        self.attachments: Dict[int, MessageAttachment] = {}
        self._next_chat_id = 1
        self._next_message_id = 1
        self._next_attachment_id = 1
    
    def create_chat(self, title: str, user_id: str, user_email: str, user_name: str) -> Chat:
        chat = Chat(
            id=self._next_chat_id,
            title=title,
            user_id=user_id,
            user_email=user_email,
            user_name=user_name
        )
        self.chats[self._next_chat_id] = chat
        self._next_chat_id += 1
        return chat
    
    def get_chat(self, chat_id: int) -> Optional[Chat]:
        return self.chats.get(chat_id)
    
    def get_user_chats(self, user_id: str, skip: int = 0, limit: int = 50) -> List[Chat]:
        user_chats = [chat for chat in self.chats.values() if chat.user_id == user_id]
        # Sort by updated_at descending
        user_chats.sort(key=lambda x: x.updated_at, reverse=True)
        return user_chats[skip:skip + limit]
    
    def update_chat(self, chat_id: int, title: str) -> Optional[Chat]:
        chat = self.chats.get(chat_id)
        if chat:
            chat.title = title
            chat.updated_at = datetime.utcnow()
        return chat
    
    def delete_chat(self, chat_id: int) -> bool:
        if chat_id in self.chats:
            # Delete associated messages and attachments
            message_ids_to_delete = [mid for mid, msg in self.messages.items() if msg.chat_id == chat_id]
            for message_id in message_ids_to_delete:
                self.delete_message(message_id)
            
            del self.chats[chat_id]
            return True
        return False
    
    def create_message(self, chat_id: int, content: str, role: str) -> ChatMessage:
        message = ChatMessage(
            id=self._next_message_id,
            chat_id=chat_id,
            content=content,
            role=role
        )
        self.messages[self._next_message_id] = message
        self._next_message_id += 1
        
        # Update chat timestamp
        if chat_id in self.chats:
            self.chats[chat_id].updated_at = datetime.utcnow()
        
        return message
    
    def get_message(self, message_id: int) -> Optional[ChatMessage]:
        return self.messages.get(message_id)
    
    def get_chat_messages(self, chat_id: int) -> List[ChatMessage]:
        chat_messages = [msg for msg in self.messages.values() if msg.chat_id == chat_id]
        # Sort by created_at ascending
        chat_messages.sort(key=lambda x: x.created_at)
        return chat_messages
    
    def delete_message(self, message_id: int) -> bool:
        if message_id in self.messages:
            # Delete associated attachments
            attachment_ids_to_delete = [aid for aid, att in self.attachments.items() if att.message_id == message_id]
            for attachment_id in attachment_ids_to_delete:
                del self.attachments[attachment_id]
            
            del self.messages[message_id]
            return True
        return False
    
    def create_attachment(self, message_id: int, filename: str, stored_filename: str, file_path: str, file_type: str) -> MessageAttachment:
        attachment = MessageAttachment(
            id=self._next_attachment_id,
            message_id=message_id,
            filename=filename,
            stored_filename=stored_filename,
            file_path=file_path,
            file_type=file_type
        )
        self.attachments[self._next_attachment_id] = attachment
        self._next_attachment_id += 1
        
        # Add attachment to message
        if message_id in self.messages:
            self.messages[message_id].attachments.append(attachment)
        
        return attachment
    
    def get_message_attachments(self, message_id: int) -> List[MessageAttachment]:
        return [att for att in self.attachments.values() if att.message_id == message_id]
    
    def get_chat_message_count(self, chat_id: int) -> int:
        return len([msg for msg in self.messages.values() if msg.chat_id == chat_id])

# Global in-memory store instance
store = Store()

def get_db() -> Store:
    return store