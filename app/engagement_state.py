from threading import Lock

_active_engagement = None
_state_lock = Lock()

def get_active_engagement():
    with _state_lock:
        return _active_engagement

def set_active_engagement(engagement_dict):
    global _active_engagement
    with _state_lock:
        _active_engagement = engagement_dict

def clear_active_engagement():
    global _active_engagement
    with _state_lock:
        _active_engagement = None
        