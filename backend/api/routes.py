import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.schemas import ChatRequest, ChatResponseUnion
from db.engine import get_db
from logger import logger
from services.chat_service import ChatService

router = APIRouter()
chat_service = ChatService()


@router.post("/chat", response_model=ChatResponseUnion)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Main chat endpoint (JSON body).

    Processes natural language queries through AI pipeline:
    1. Entity extraction
    2. Intent classification
    3. SQL generation
    4. Validation
    5. Execution
    6. Response formatting
    """
    try:
        response = await chat_service.handle_query(
            request.query,
            db,
            conversation_id=request.conversation_id,
            clarification_selection=request.clarification_selection,
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/chat/upload", response_model=ChatResponseUnion)
async def chat_upload(
    query: str | None = Form(None),
    conversation_id: str | None = Form(None),
    clarification_selection: str | None = Form(None),
    files: list[UploadFile] | None = File(None),
    db: Session = Depends(get_db),
):
    """
    Chat with file attachments (multipart/form-data).
    Parses files, persists rows under the uploads schema (see ChatService),
    and returns preview data. Does not run the full NL→SQL pipeline in this
    request; use POST /api/chat with the same conversation_id for questions.
    """
    try:
        if not files:
            raise HTTPException(
                status_code=400,
                detail="No files uploaded. Use POST /api/chat with JSON for text-only queries.",
            )

        parsed_clarification = None
        if clarification_selection:
            try:
                parsed_clarification = json.loads(clarification_selection)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400, detail="Invalid clarification_selection format"
                )

        chat_request = ChatRequest(
            query=query or "",
            conversation_id=conversation_id,
            clarification_selection=parsed_clarification,
        )

        cid = (conversation_id or "").strip() or str(uuid.uuid4())
        response = await chat_service.handle_file_query(
            chat_request.query, files, db, cid
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "AI Data Extraction Chatbot",
    }


@router.get("/schema")
async def schema_info():
    return {
        "ecommerce": {
            "customers": ["id", "name", "email", "location", "created_at"],
            "orders": [
                "id",
                "customer_id",
                "order_date",
                "total_value",
                "status",
                "created_at",
            ],
            "products": ["id", "name", "category_id", "price", "created_at"],
            "categories": ["id", "name", "description"],
        },
        "support": {
            "customers": [
                "id",
                "name",
                "email",
                "contact_info",
                "account_status",
                "created_at",
            ],
            "tickets": [
                "id",
                "customer_id",
                "title",
                "description",
                "status",
                "priority",
                "assigned_agent_id",
                "created_at",
                "updated_at",
            ],
            "agents": ["id", "name", "department", "email"],
            "ticket_notes": ["id", "ticket_id", "agent_id", "note", "created_at"],
        },
        "uploads": {
            "datasets": [
                "id",
                "conversation_id",
                "file_name",
                "row_count",
                "created_at",
            ],
            "dataset_rows": ["id", "dataset_id", "row_index", "data"],
        },
    }


@router.get("/suggested-queries")
async def suggested_queries():
    return {
        "queries": [
            "Show me all orders from customer Hina Patel in the last month",
            "List all open support tickets for customer Ben Okafor",
            "What is the total order value for each customer who has opened support tickets?",
            "Find customers who have made purchases but never raised support tickets",
        ]
    }