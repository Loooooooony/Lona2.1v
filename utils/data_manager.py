import json
import os
import asyncio

# Global Locks
_locks = {}


def _get_lock(path):
    if path not in _locks:
        _locks[path] = asyncio.Lock()
    return _locks[path]


def get_guild_folder(guild_id):
    path = f'data/guilds/{guild_id}/'
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path


def get_guild_file(guild_id, filename):
    folder = get_guild_folder(guild_id)
    if '/' in filename:
        sub_path = os.path.join(folder, os.path.dirname(filename))
        if not os.path.exists(sub_path):
            os.makedirs(sub_path, exist_ok=True)
    return os.path.join(folder, filename)


def get_guild_asset(guild_id, filename, default_path=None):
    """
    Returns path to guild specific asset if exists, else default global asset.
    """
    g_path = get_guild_file(guild_id, f'images/{filename}')
    if os.path.exists(g_path):
        return g_path

    # Check default path
    if default_path and os.path.exists(default_path):
        return default_path

    return None


async def load_guild_json(guild_id, filename, default=None):
    if default is None:
        default = {}
    path = get_guild_file(guild_id, filename)
    lock = _get_lock(path)
    async with lock:
        if not os.path.exists(path):
            return default
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default


async def save_guild_json(guild_id, filename, data):
    path = get_guild_file(guild_id, filename)
    lock = _get_lock(path)
    async with lock:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


def check_guild_password(guild_id, password_input):
    try:
        with open('data/server_passwords.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get(str(guild_id)) == password_input
    except Exception:
        return False


def set_guild_password(guild_id, password):
    try:
        with open('data/server_passwords.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        data = {}

    data[str(guild_id)] = password
    with open('data/server_passwords.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
