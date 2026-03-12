from pathlib import Path

import yaml

CONFIG_PATH = Path.home() / ".garage133.yaml"

def load_config():
    """Loads the persistent configuration."""
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open('r') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}

def save_config(updates):
    """Updates and saves the persistent configuration."""
    config = load_config()
    config.update(updates)
    try:
        with CONFIG_PATH.open('w') as f:
            yaml.dump(config, f, default_flow_style=False)
        print(f"Config updated: {CONFIG_PATH}")
    except Exception as e:
        print(f"Error saving config: {e}")

def get_root_dir(cli_arg=None):
    """Determines the root directory based on CLI, config, or current dir."""
    if cli_arg:
        return Path(cli_arg).resolve()
    
    config = load_config()
    cached_dir = config.get("root_dir")
    if cached_dir:
        return Path(cached_dir).resolve()
    
    return Path.cwd()
