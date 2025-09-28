import time
from Sakura.Core.config import MESSAGE_LIMIT, RATE_LIMIT_COUNT, RATE_LIMIT_TTL
from Sakura.Core.logging import logger
from Sakura.Storage.valkey import valkey_client
from Sakura.application import user_message_counts, rate_limited_users

async def check_limit(user_id: int, chat_id: int) -> bool:
    """
    Checks if a user is rate-limited based on a per-user, per-chat basis.
    """
    if valkey_client:
        try:
            hard_limit_key = f"hard_rate_limit:{user_id}:{chat_id}"
            if await valkey_client.exists(hard_limit_key):
                return True

            message_count_key = f"message_count:{user_id}:{chat_id}"
            pipe = valkey_client.pipeline()
            pipe.incr(message_count_key)
            pipe.ttl(message_count_key)
            results = await pipe.execute()

            count = results[0]
            ttl = results[1]

            if ttl == -1:
                await valkey_client.expire(message_count_key, int(MESSAGE_LIMIT))

            if count > RATE_LIMIT_COUNT:
                await valkey_client.setex(hard_limit_key, RATE_LIMIT_TTL, "1")
                return True

            if count > 1:
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Valkey rate limit check failed for user {user_id}:{chat_id}: {e}. Falling back to memory.")

    key = f"{user_id}:{chat_id}"
    current_time = time.time()

    if key in rate_limited_users and current_time < rate_limited_users[key]:
        return True
    elif key in rate_limited_users:
        del rate_limited_users[key]

    timestamps = user_message_counts.get(key, [])
    timestamps = [ts for ts in timestamps if current_time - ts < MESSAGE_LIMIT]
    timestamps.append(current_time)
    user_message_counts[key] = timestamps

    if len(timestamps) > RATE_LIMIT_COUNT:
        rate_limited_users[key] = current_time + RATE_LIMIT_TTL
        return True

    if len(timestamps) > 1:
        return True

    return False