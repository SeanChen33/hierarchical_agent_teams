from contextvars import ContextVar
import uuid
import time
import logging

logger = logging.getLogger(__name__)

# Core context variables for hierarchical agent teams
current_team: ContextVar[str] = ContextVar("current_team", default="")
current_node: ContextVar[str] = ContextVar("current_node", default="")
current_request_id: ContextVar[str] = ContextVar("current_request_id", default="")

# Minimal request metadata tracking
_request_metadata: ContextVar[dict] = ContextVar("request_metadata", default=None)


def init_request_context(conversation_id: str = None, user_message: str = None) -> str:
	"""Initialize minimal request context."""
	request_id = str(uuid.uuid4())[:8]
	current_request_id.set(request_id)
	
	# Initialize minimal metadata
	metadata = {
		"request_id": request_id,
		"conversation_id": conversation_id,
		"start_time": time.time(),
		"user_message": user_message,
		"status": "active"
	}
	_request_metadata.set(metadata)
	
	logger.info(f"Initialized request context: {request_id}")
	return request_id


def update_request_status(status: str) -> None:
	"""Update request status."""
	metadata = _request_metadata.get()
	if metadata:
		metadata["status"] = status
		metadata["updated_time"] = time.time()


def get_request_metadata() -> dict:
	"""Get current request metadata."""
	return dict(_request_metadata.get() or {})