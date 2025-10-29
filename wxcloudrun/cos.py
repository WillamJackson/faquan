import os
from typing import Tuple, Optional, Dict

from qcloud_cos import CosConfig, CosS3Client
import requests

import config


_sts_cache: Dict[str, str] = {}


def _assert_cos_env():
    if not config.cos_bucket:
        raise RuntimeError("缺少环境变量: COS_BUCKET")
    if not config.cos_region:
        raise RuntimeError("缺少环境变量: COS_REGION")
    # 若未启用 STS，则校验永久密钥；若启用 STS，则校验临时密钥
    if not config.cos_use_sts:
        if not config.cos_secret_id:
            raise RuntimeError("缺少环境变量: COS_SECRET_ID")
        if not config.cos_secret_key:
            raise RuntimeError("缺少环境变量: COS_SECRET_KEY")
    else:
        # 如未配置环境变量临时密钥，尝试通过开放接口 URL 拉取
        if not (config.cos_tmp_secret_id and config.cos_tmp_secret_key and config.cos_token):
            if not (config.cloudrun_sts_url or config.cloudrun_open_service_base):
                raise RuntimeError("未配置永久密钥，且缺少 STS 拉取 URL: CLOUDRUN_STS_URL 或 CLOUDRUN_OPEN_SERVICE_BASE")


def get_client() -> CosS3Client:
    """构造 COS 客户端实例（支持 STS 临时密钥）"""
    _assert_cos_env()
    if config.cos_use_sts:
        creds = _get_sts_cached()
        if not creds and not (config.cos_tmp_secret_id and config.cos_tmp_secret_key and config.cos_token):
            creds = _fetch_sts()
            if creds:
                _sts_cache.update(creds)
        sid = creds.get('tmpSecretId') if creds else config.cos_tmp_secret_id
        sk = creds.get('tmpSecretKey') if creds else config.cos_tmp_secret_key
        tok = creds.get('sessionToken') if creds else config.cos_token
        conf = CosConfig(
            Region=config.cos_region,
            SecretId=sid,
            SecretKey=sk,
            Token=tok,
            Scheme='https',
        )
    else:
        conf = CosConfig(
            Region=config.cos_region,
            SecretId=config.cos_secret_id,
            SecretKey=config.cos_secret_key,
            Token=None,
            Scheme='https',
        )
    return CosS3Client(conf)


def health_check() -> Tuple[bool, Optional[str]]:
    """检查 COS 存储桶可达性"""
    try:
        client = get_client()
        client.head_bucket(Bucket=config.cos_bucket)
        return True, None
    except Exception as e:
        return False, str(e)


def upload_bytes(key: str, content: bytes, content_type: str = 'application/octet-stream', metadata: Optional[Dict[str, str]] = None) -> Tuple[dict, str]:
    """上传二进制内容到 COS 并返回访问 URL。metadata 为自定义元数据字典（例如 {'fileid': '...'}）。"""
    client = get_client()
    kwargs = {
        'Bucket': config.cos_bucket,
        'Body': content,
        'Key': key,
        'ContentType': content_type,
    }
    if metadata:
        kwargs['Metadata'] = metadata
    resp = client.put_object(**kwargs)
    base = config.cos_base_url()
    url = f"{base}/{key}" if base else ""
    return resp, url


def encode_metaid(openid: str, upload_dir: str, timeout: int = 10) -> Optional[str]:
    """调用开放接口服务生成 x-cos-meta-fileid。

    依赖环境变量 CLOUDRUN_OPEN_SERVICE_BASE，形如 https://<服务域名>。
    openid 来源于小程序请求头 "x-openid"。
    返回 metaid 字符串，失败时返回 None。
    """
    # 优先使用完整 URL，其次拼装基地址与常见路径（大小写兼容）
    full = (config.cloudrun_metaid_url or '').strip()
    if full:
        url_candidates = [full]
    else:
        base = (config.cloudrun_open_service_base or '').strip().rstrip('/')
        if not base:
            return None
        suffixes = [
            '/_/cos/metaid/encode',
            '/_/cos/metaId/encode',
            '/_/cos/metaid/Encode',
        ]
        url_candidates = [f"{base}{suf}" for suf in suffixes]
    for url in url_candidates:
        try:
            r = requests.post(url, json={
                'openid': openid,
                'bucket': config.cos_bucket,
                'dir': upload_dir,
            }, timeout=timeout)
            if r.status_code >= 400:
                continue
            data = r.json()
            arr = data.get('x_cos_meta_field_strs') or []
            if isinstance(arr, list) and arr:
                return arr[0]
            mid = data.get('metaid')
            if mid:
                return mid
        except Exception:
            continue
    return None
def _fetch_sts() -> Optional[Dict[str, str]]:
    """通过开放接口获取 STS 临时凭证，返回字典包含 tmpSecretId/tmpSecretKey/sessionToken/expiredTime。

    兼容多种端点：
    - 明确完整 URL：CLOUDRUN_STS_URL
    - 仅提供基地址：CLOUDRUN_OPEN_SERVICE_BASE（将尝试多种常见路径及大小写）
    """
    url_conf = (config.cloudrun_sts_url or '').strip()
    base = (config.cloudrun_open_service_base or '').strip().rstrip('/')

    candidates = []

    # 若提供的是完整 URL（包含 /_/cos/），优先尝试该 URL；否则视作基地址
    if url_conf:
        if '/_/' in url_conf:
            candidates.append(url_conf)
        else:
            base = url_conf.rstrip('/')

    # 基地址下的常见路径（大小写兼容）
    if base:
        suffixes = [
            '/_/cos/getauthorization',
            '/_/cos/getAuthorization',
            '/_/cos/getauth',
            '/_/cos/getAuth',
        ]
        candidates.extend([f"{base}{suf}" for suf in suffixes])

    # 去重保持顺序
    seen = set()
    seq = []
    for u in candidates:
        if u not in seen:
            seq.append(u)
            seen.add(u)

    for url in seq:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code >= 400:
                continue
            data = r.json() or {}
            # 兼容字段名
            tsid = data.get('tmpSecretId') or data.get('TmpSecretId')
            tsk = data.get('tmpSecretKey') or data.get('TmpSecretKey')
            tok = data.get('sessionToken') or data.get('Token')
            exp = data.get('expiredTime') or data.get('ExpiredTime')
            if tsid and tsk and tok:
                return {
                    'tmpSecretId': tsid,
                    'tmpSecretKey': tsk,
                    'sessionToken': tok,
                    'expiredTime': str(exp or ''),
                }
        except Exception:
            continue
    return None


def _get_sts_cached() -> Optional[Dict[str, str]]:
    """返回有效的 STS 缓存，若即将过期则忽略。"""
    if not _sts_cache:
        return None
    try:
        exp = int(_sts_cache.get('expiredTime', '0'))
    except Exception:
        return None
    import time
    now = int(time.time())
    # 预留 60s 缓冲
    if exp and (exp - now) > 60:
        return _sts_cache
    return None