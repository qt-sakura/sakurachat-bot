from typing import Dict, Set, Optional, List
from pyrogram import Client
from valkey.asyncio import Valkey as AsyncValkey
from sambanova import SambaNova

# GLOBAL STATE & MEMORY SYSTEM
user_ids: Set[int] = set()
group_ids: Set[int] = set()
broadcast_mode: Dict[int, str] = {}
user_message_counts: Dict[str, List] = {}
rate_limited_users: Dict[str, float] = {}
user_last_response_time: Dict[int, float] = {}
conversation_history: Dict[int, list] = {}
db_pool = None
cleanup_task = None
valkey_client: Optional[AsyncValkey] = None
payment_storage: Dict[str, dict] = {}
effects_client: Optional[Client] = None
sambanova_client: Optional[SambaNova] = None