from datetime import datetime
import uuid
from flask import render_template, request
from run import app
import config
from wxcloudrun.__init__ import db
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.model import Counters
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response
from wxcloudrun.cos import health_check as cos_health_check, upload_bytes, encode_metaid


@app.route('/')
def index():
    """
    :return: 返回index页面
    """
    return render_template('index.html')


@app.route('/api/count', methods=['POST'])
def count():
    """
    :return:计数结果/清除结果
    """

    # 获取请求体参数
    params = request.get_json()

    # 检查action参数
    if 'action' not in params:
        return make_err_response('缺少action参数')

    # 按照不同的action的值，进行不同的操作
    action = params['action']

    # 执行自增操作
    if action == 'inc':
        counter = query_counterbyid(1)
        if counter is None:
            counter = Counters()
            counter.id = 1
            counter.count = 1
            counter.created_at = datetime.now()
            counter.updated_at = datetime.now()
            insert_counter(counter)
        else:
            counter.id = 1
            counter.count += 1
            counter.updated_at = datetime.now()
            update_counterbyid(counter)
        return make_succ_response(counter.count)

    # 执行清0操作
    elif action == 'clear':
        delete_counterbyid(1)
        return make_succ_empty_response()

    # action参数错误
    else:
        return make_err_response('action参数错误')


@app.route('/api/count', methods=['GET'])
def get_count():
    """
    :return: 计数的值
    """
    counter = Counters.query.filter(Counters.id == 1).first()
    return make_succ_response(0) if counter is None else make_succ_response(counter.count)


@app.route('/api/storage/cos/health', methods=['GET'])
def cos_health():
    """COS 存储桶健康检查"""
    ok, err = cos_health_check()
    if ok:
        return make_succ_response({
            'healthy': True,
            'bucket': config.cos_bucket,
            'region': config.cos_region,
            'base_url': config.cos_base_url(),
        })
    else:
        return make_err_response(f'COS健康检查失败: {err}')


@app.route('/api/db/health', methods=['GET'])
def db_health():
    """数据库健康检查"""
    try:
        db.session.execute('SELECT 1')
        return make_succ_response({
            'healthy': True,
            'database': config.db_name,
            'address': config.db_address,
        })
    except Exception as e:
        return make_err_response(f'数据库健康检查失败: {e}')


@app.route('/api/storage/upload', methods=['POST'])
def storage_upload():
    """上传文件到 COS

    请求格式：multipart/form-data，字段：
    - file: 文件内容
    - key: 目标对象键（可选），为空时自动生成
    """
    file = request.files.get('file')
    key = request.form.get('key')

    if not file:
        return make_err_response('缺少文件字段: file')

    if not key:
        filename = file.filename or 'file.bin'
        uid = uuid.uuid4().hex
        key = f'uploads/{datetime.now().strftime("%Y%m%d")}/{uid}-{filename}'

    content_type = file.mimetype or 'application/octet-stream'

    # 生成上传目录用于元数据编码
    upload_dir = '/'.join(key.split('/')[:-1]) if '/' in key else ''

    # 读取 openid（兼容 x-wx-openid 与 x-openid）
    openid = request.headers.get('x-wx-openid') or request.headers.get('x-openid')

    # 调用开放接口服务生成 metaid（若配置了 CLOUDRUN_OPEN_SERVICE_BASE 且带有 openid）
    metaid = None
    if openid and config.cloudrun_open_service_base:
        metaid = encode_metaid(openid=openid, upload_dir=upload_dir)

    metadata = {'fileid': metaid} if metaid else None

    try:
        _, url = upload_bytes(key, file.read(), content_type, metadata)
        data = {'key': key, 'url': url}
        if metaid:
            data['metaid'] = metaid
        return make_succ_response(data)
    except Exception as e:
        return make_err_response(f'上传失败: {e}')
