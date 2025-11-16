# app/secrets.py
import os
import json
from typing import Any, Dict, Optional

# Lazy cache for loaded remote secret JSON blobs
_SECRETS_CACHE: Dict[str, Dict[str, Any]] = {}

def _load_aws_secret_json(secret_name: str) -> Dict[str, Any]:
    if secret_name in _SECRETS_CACHE:
        return _SECRETS_CACHE[secret_name]
    try:
        import boto3
        client = boto3.client('secretsmanager', region_name=os.getenv('AWS_REGION'))
        resp = client.get_secret_value(SecretId=secret_name)
        secret_string = resp.get('SecretString')
        if secret_string:
            parsed = json.loads(secret_string)
        else:
            parsed = {}
        _SECRETS_CACHE[secret_name] = parsed
        return parsed
    except Exception:
        return {}

def _load_vault_kv(path: str) -> Dict[str, Any]:
    if path in _SECRETS_CACHE:
        return _SECRETS_CACHE[path]
    try:
        import hvac
        client = hvac.Client(url=os.getenv('VAULT_ADDR'), token=os.getenv('VAULT_TOKEN'))
        resp = client.secrets.kv.v2.read_secret_version(path=path)
        data = resp['data']['data']
        _SECRETS_CACHE[path] = data
        return data
    except Exception:
        return {}

def get(key: str, default: Optional[str] = None) -> Optional[str]:
    # 1) env var direct
    val = os.getenv(key)
    if val is not None:
        return val

    # 2) AWS Secrets Manager (single JSON secret)
    aws_secret_name = os.getenv('AWS_SECRET_NAME')
    if aws_secret_name:
        aws_json = _load_aws_secret_json(aws_secret_name)
        if key in aws_json:
            return str(aws_json[key])

    # 3) Vault KV
    vault_path = os.getenv('VAULT_SECRET_PATH')
    if vault_path:
        vault_json = _load_vault_kv(vault_path)
        if key in vault_json:
            return str(vault_json[key])

    return default

def get_json(secret_name: str) -> Dict[str, Any]:
    raw = os.getenv(secret_name)
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            return {}
    aws_secret_name = os.getenv('AWS_SECRET_NAME')
    if aws_secret_name and aws_secret_name == secret_name:
        return _load_aws_secret_json(aws_secret_name)
    return {}