from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import json

from ...utils import get_db
from ...services.auth_service import get_current_user
from ...models import User, Chat, ChatMessage

router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic schemas for request/response validation
from pydantic import BaseModel, Field


class ChatMessageCreate(BaseModel):
    role: str
    content: str
    message_metadata: Optional[Dict[str, Any]] = None


class ChatCreate(BaseModel):
    system_prompt: Optional[str] = None
    model_id: str
    model_name: Optional[str] = None
    model_provider: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    messages: List[ChatMessageCreate]


class ChatUpdate(BaseModel):
    title: Optional[str] = None


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    order: int
    message_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class ChatResponse(BaseModel):
    id: int
    title: Optional[str] = None
    system_prompt: Optional[str] = None
    model_id: str
    model_name: Optional[str] = None
    model_provider: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    messages: List[ChatMessageResponse] = []


@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_data: ChatCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new chat with its messages."""
    try:
        logger.info(f"Received request to create chat: model_id={chat_data.model_id}, user_id={current_user.id}")
        logger.info(f"Chat data contains {len(chat_data.messages)} messages")
        logger.info(f"System prompt: {chat_data.system_prompt}")
        logger.info(f"Full chat data: {chat_data}")
        
        # Create chat title from first message if available
        title = None
        if chat_data.messages and len(chat_data.messages) > 0:
            # Get the first user message
            user_messages = [m for m in chat_data.messages if m.role == 'user']
            if user_messages:
                # Create title from first few characters
                title = user_messages[0].content[:30] + ("..." if len(user_messages[0].content) > 30 else "")
        
        logger.info(f"Created title: {title}")
        
        # Create chat object
        chat = Chat(
            user_id=current_user.id,
            title=title,
            system_prompt=chat_data.system_prompt,
            model_id=chat_data.model_id,
            model_name=chat_data.model_name,
            model_provider=chat_data.model_provider,
            configuration=chat_data.configuration
        )
        
        logger.info(f"Created chat object: {chat.__dict__}")
        
        # Add to database
        db.add(chat)
        await db.flush()  # To get the chat ID
        logger.info(f"Flushed chat to DB, got ID: {chat.id}")
        
        # Add messages
        for i, msg_data in enumerate(chat_data.messages):
            message = ChatMessage(
                chat_id=chat.id,
                role=msg_data.role,
                content=msg_data.content,
                order=i,
                message_metadata=msg_data.message_metadata
            )
            logger.info(f"Adding message {i}: role={msg_data.role}, content preview={msg_data.content[:30] if msg_data.content else None}")
            db.add(message)
        
        logger.info("Committing transaction")
        await db.commit()
        logger.info("Transaction committed successfully")
        
        # Refresh to get the full object with relationships
        await db.refresh(chat)
        logger.info("Chat object refreshed")
        
        # Explicitly query for messages instead of using chat.messages
        msg_stmt = select(ChatMessage).where(ChatMessage.chat_id == chat.id).order_by(ChatMessage.order)
        msg_result = await db.execute(msg_stmt)
        messages = msg_result.scalars().all()
        logger.info(f"Retrieved {len(messages)} messages for chat {chat.id}")
        
        # Convert to response model
        response = {
            "id": chat.id,
            "title": chat.title,
            "system_prompt": chat.system_prompt,
            "model_id": chat.model_id,
            "model_name": chat.model_name,
            "model_provider": chat.model_provider,
            "configuration": chat.configuration,
            "created_at": chat.created_at,
            "updated_at": chat.updated_at,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "order": msg.order,
                    "message_metadata": msg.message_metadata,
                    "created_at": msg.created_at
                }
                for msg in messages
            ]
        }
        
        logger.info(f"Returning response with chat ID: {chat.id}")
        return response
    
    except Exception as e:
        logger.error(f"Error creating chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chat: {str(e)}"
        )


@router.get("/", response_model=List[ChatResponse])
async def get_user_chats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """Get all chats for the current user."""
    try:
        stmt = select(Chat).where(Chat.user_id == current_user.id).order_by(desc(Chat.updated_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        chats = result.scalars().all()
        
        chat_responses = []
        for chat in chats:
            # Query messages for this chat
            msg_stmt = select(ChatMessage).where(ChatMessage.chat_id == chat.id).order_by(ChatMessage.order)
            msg_result = await db.execute(msg_stmt)
            messages = msg_result.scalars().all()
            
            chat_responses.append({
                "id": chat.id,
                "title": chat.title,
                "system_prompt": chat.system_prompt,
                "model_id": chat.model_id,
                "model_name": chat.model_name,
                "model_provider": chat.model_provider,
                "configuration": chat.configuration,
                "created_at": chat.created_at,
                "updated_at": chat.updated_at,
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "order": msg.order,
                        "message_metadata": msg.message_metadata,
                        "created_at": msg.created_at
                    }
                    for msg in messages
                ]
            })
        
        return chat_responses
        
    except Exception as e:
        logger.error(f"Error getting chats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chats: {str(e)}"
        )


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific chat by ID."""
    try:
        stmt = select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id)
        result = await db.execute(stmt)
        chat = result.scalars().first()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat with ID {chat_id} not found"
            )
        
        # Query messages for this chat
        msg_stmt = select(ChatMessage).where(ChatMessage.chat_id == chat.id).order_by(ChatMessage.order)
        msg_result = await db.execute(msg_stmt)
        messages = msg_result.scalars().all()
        
        return {
            "id": chat.id,
            "title": chat.title,
            "system_prompt": chat.system_prompt,
            "model_id": chat.model_id,
            "model_name": chat.model_name,
            "model_provider": chat.model_provider,
            "configuration": chat.configuration,
            "created_at": chat.created_at,
            "updated_at": chat.updated_at,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "order": msg.order,
                    "message_metadata": msg.message_metadata,
                    "created_at": msg.created_at
                }
                for msg in messages
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat {chat_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat: {str(e)}"
        )


@router.post("/{chat_id}/messages", response_model=ChatMessageResponse)
async def add_message_to_chat(
    chat_id: int,
    message: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a new message to an existing chat."""
    try:
        # Verify chat exists and belongs to user
        stmt = select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id)
        result = await db.execute(stmt)
        chat = result.scalars().first()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat with ID {chat_id} not found"
            )
        
        # Get current max order
        msg_stmt = select(ChatMessage).where(ChatMessage.chat_id == chat_id).order_by(desc(ChatMessage.order))
        msg_result = await db.execute(msg_stmt)
        latest_msg = msg_result.scalars().first()
        
        new_order = 0
        if latest_msg:
            new_order = latest_msg.order + 1
        
        # Create new message
        new_message = ChatMessage(
            chat_id=chat_id,
            role=message.role,
            content=message.content,
            order=new_order,
            message_metadata=message.message_metadata
        )
        
        db.add(new_message)
        
        # Update chat's updated_at timestamp
        chat.updated_at = datetime.now()
        
        await db.commit()
        await db.refresh(new_message)
        
        return {
            "id": new_message.id,
            "role": new_message.role,
            "content": new_message.content,
            "order": new_message.order,
            "message_metadata": new_message.message_metadata,
            "created_at": new_message.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding message to chat {chat_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add message: {str(e)}"
        )


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a chat and all its messages."""
    try:
        # Verify chat exists and belongs to user
        stmt = select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id)
        result = await db.execute(stmt)
        chat = result.scalars().first()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat with ID {chat_id} not found"
            )
        
        # Delete the chat (cascade will delete messages)
        await db.delete(chat)
        await db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chat {chat_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chat: {str(e)}"
        )


@router.put("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: int,
    chat_data: ChatUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update chat metadata."""
    try:
        # Verify chat exists and belongs to user
        stmt = select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id)
        result = await db.execute(stmt)
        chat = result.scalars().first()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat with ID {chat_id} not found"
            )
        
        # Update fields
        if chat_data.title is not None:
            chat.title = chat_data.title
        
        # Update timestamp
        chat.updated_at = datetime.now()
        
        await db.commit()
        await db.refresh(chat)
        
        # Query messages for this chat
        msg_stmt = select(ChatMessage).where(ChatMessage.chat_id == chat.id).order_by(ChatMessage.order)
        msg_result = await db.execute(msg_stmt)
        messages = msg_result.scalars().all()
        
        return {
            "id": chat.id,
            "title": chat.title,
            "system_prompt": chat.system_prompt,
            "model_id": chat.model_id,
            "model_name": chat.model_name,
            "model_provider": chat.model_provider,
            "configuration": chat.configuration,
            "created_at": chat.created_at,
            "updated_at": chat.updated_at,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "order": msg.order,
                    "message_metadata": msg.message_metadata,
                    "created_at": msg.created_at
                }
                for msg in messages
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating chat {chat_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update chat: {str(e)}"
        ) 