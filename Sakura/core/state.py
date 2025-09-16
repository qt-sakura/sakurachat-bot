from typing import Dict, Set

user_ids: Set[int] = set()
group_ids: Set[int] = set()
help_expanded: Dict[int, bool] = {}
broadcast_mode: Dict[int, str] = {}
user_message_counts: Dict[str, list] = {}
rate_limited_users: Dict[str, float] = {}
user_last_response_time: Dict[int, float] = {}
conversation_history: Dict[int, list] = {}
payment_storage: Dict[str, dict] = {}
