import os

# 是否开启debug模式
DEBUG = True

# 读取数据库环境变量
username = os.environ.get("MYSQL_USERNAME", 'root')
password = os.environ.get("MYSQL_PASSWORD", 'FcV7MuKy')
db_address = os.environ.get("MYSQL_ADDRESS", 'sh-cynosdbmysql-grp-kb30a7co.sql.tencentcdb.com:23900')
db_name = os.environ.get("MYSQL_DBNAME", 'faquan')

# 对象存储（COS）环境变量
cos_bucket = os.environ.get("COS_BUCKET", '7072-prod-8gd9pf8aaa4c364f-1256841508')
cos_region = os.environ.get("COS_REGION", 'ap-shanghai')
cos_secret_id = os.environ.get("COS_SECRET_ID", '')
cos_secret_key = os.environ.get("COS_SECRET_KEY", '')

# STS 临时密钥与开放接口服务（可选）
cos_use_sts = os.environ.get("COS_USE_STS", 'true').lower() == 'true'
cos_tmp_secret_id = os.environ.get("COS_TMP_SECRET_ID", '')
cos_tmp_secret_key = os.environ.get("COS_TMP_SECRET_KEY", '')
cos_token = os.environ.get("COS_TOKEN", '')
cloudrun_open_service_base = os.environ.get("CLOUDRUN_OPEN_SERVICE_BASE", '')

# 开放接口完整 URL（可选，若提供则优先使用）
cloudrun_sts_url = os.environ.get("CLOUDRUN_STS_URL", 'https://flask-yztr-195628-4-1256841508.sh.run.tcloudbase.com')
cloudrun_metaid_url = os.environ.get("CLOUDRUN_METAID_URL", '')

# COS 公网访问域名（按桶与地域拼装）
def cos_base_url(bucket: str = None, region: str = None) -> str:
    b = (bucket or cos_bucket).strip()
    r = (region or cos_region).strip()
    if not b or not r:
        return ''
    return f"https://{b}.cos.{r}.myqcloud.com"
