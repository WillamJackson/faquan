# wxcloudrun-flask
[![GitHub license](https://img.shields.io/github/license/WeixinCloud/wxcloudrun-express)](https://github.com/WeixinCloud/wxcloudrun-express)
![GitHub package.json dependency version (prod)](https://img.shields.io/badge/python-3.7.3-green)

微信云托管 python Flask 框架模版，实现简单的计数器读写接口，使用云托管 MySQL 读写、记录计数值。

![](https://qcloudimg.tencent-cloud.cn/raw/be22992d297d1b9a1a5365e606276781.png)


## 快速开始
前往 [微信云托管快速开始页面](https://developers.weixin.qq.com/miniprogram/dev/wxcloudrun/src/basic/guide.html)，选择相应语言的模板，根据引导完成部署。

## 本地调试
下载代码在本地调试，请参考[微信云托管本地调试指南](https://developers.weixin.qq.com/miniprogram/dev/wxcloudrun/src/guide/debug/)

## 实时开发
代码变动时，不需要重新构建和启动容器，即可查看变动后的效果。请参考[微信云托管实时开发指南](https://developers.weixin.qq.com/miniprogram/dev/wxcloudrun/src/guide/debug/dev.html)

## Dockerfile最佳实践
请参考[如何提高项目构建效率](https://developers.weixin.qq.com/miniprogram/dev/wxcloudrun/src/scene/build/speed.html)

## 目录结构说明

~~~
.
├── Dockerfile dockerfile       dockerfile
├── README.md README.md         README.md文件
├── container.config.json       模板部署「服务设置」初始化配置（二开请忽略）
├── requirements.txt            依赖包文件
├── config.py                   项目的总配置文件  里面包含数据库 web应用 日志等各种配置
├── run.py                      flask项目管理文件 与项目进行交互的命令行工具集的入口
└── wxcloudrun                  app目录
    ├── __init__.py             python项目必带  模块化思想
    ├── dao.py                  数据库访问模块
    ├── model.py                数据库对应的模型
    ├── response.py             响应结构构造
    ├── templates               模版目录,包含主页index.html文件
    └── views.py                执行响应的代码所在模块  代码逻辑处理主要地点  项目大部分代码在此编写
~~~



## 服务 API 文档

### `GET /api/count`

获取当前计数

#### 请求参数

无

#### 响应结果

- `code`：错误码
- `data`：当前计数值

##### 响应结果示例

```json
{
  "code": 0,
  "data": 42
}
```

#### 调用示例

```
curl https://<云托管服务域名>/api/count
```



### `POST /api/count`

更新计数，自增或者清零

#### 请求参数

- `action`：`string` 类型，枚举值
  - 等于 `"inc"` 时，表示计数加一
  - 等于 `"clear"` 时，表示计数重置（清零）

##### 请求参数示例

```
{
  "action": "inc"
}
```

#### 响应结果

- `code`：错误码
- `data`：当前计数值

##### 响应结果示例

```json
{
  "code": 0,
  "data": 42
}
```

#### 调用示例

```
curl -X POST -H 'content-type: application/json' -d '{"action": "inc"}' https://<云托管服务域名>/api/count
```

### `GET /api/db/health`

数据库健康检查，返回数据库可用性与连接信息。

#### 响应结果

- `code`: 错误码（0 为成功）
- `data.healthy`: 是否健康
- `data.database`: 数据库名
- `data.address`: 数据库地址

#### 调用示例

```
curl https://<云托管服务域名>/api/db/health
```

### `GET /api/storage/cos/health`

COS 对象存储健康检查，返回存储桶可用性与基础访问域名。

#### 响应结果

- `code`: 错误码（0 为成功）
- `data.healthy`: 是否健康
- `data.bucket`: 存储桶名称
- `data.region`: 存储桶地域
- `data.base_url`: 访问基础域名

#### 调用示例

```
curl https://<云托管服务域名>/api/storage/cos/health
```

### `POST /api/storage/upload`

上传文件到 COS。请求格式：`multipart/form-data`

#### 请求参数

- `file`: 文件内容（二进制，必填）
- `key`: 目标对象键（可选，未提供时自动生成）

#### 响应结果

- `code`: 错误码（0 为成功）
- `data.key`: 对象键
- `data.url`: 公网访问 URL（若配置了公开访问域名）

#### 调用示例

```
curl -X POST \
  -F "file=@/path/to/local.png" \
  -F "key=uploads/20250101/test.png" \
  https://<云托管服务域名>/api/storage/upload
```

## 使用注意
如果不是通过微信云托管控制台部署模板代码，而是自行复制/下载模板代码后，手动新建一个服务并部署，需要在「服务设置」中补全以下环境变量，才可正常使用，否则会引发无法连接数据库，进而导致部署失败。
- MYSQL_ADDRESS
- MYSQL_PASSWORD
- MYSQL_USERNAME
- MYSQL_DBNAME（可选，默认 `flask_demo`）
以上三个变量的值请按实际情况填写。如果使用云托管内MySQL，可以在控制台MySQL页面获取相关信息。

此外，如需启用 COS 上传与健康检查，请在「服务设置」中补全下列对象存储相关环境变量：

- COS_BUCKET：如 `7072-prod-8gd9pf8aaa4c364f-1256841508`
- COS_REGION：如 `ap-shanghai`
- COS_SECRET_ID：腾讯云访问密钥 SecretId
- COS_SECRET_KEY：腾讯云访问密钥 SecretKey

当全部 COS 变量配置完成后，可调用 `/api/storage/cos/health` 验证可用性，并使用 `/api/storage/upload` 上传文件。

### 云托管最佳实践：临时密钥 + 元数据

为满足小程序直传回读的安全与可控性，推荐开启“临时密钥 + 元数据”模式（纯 STS，无需永久密钥）：

- 环境变量（服务设置）
  - 基本：`COS_BUCKET`、`COS_REGION`
  - 启用 STS：`COS_USE_STS=true`
  - STS 获取方式（二选一）：
    - 方式 A（静态注入，便于本地调试）：`COS_TMP_SECRET_ID`、`COS_TMP_SECRET_KEY`、`COS_TOKEN`
    - 方式 B（动态拉取，生产推荐）：`CLOUDRUN_STS_URL=<开放接口完整URL>` 或 `CLOUDRUN_OPEN_SERVICE_BASE=https://<服务域名>`（默认路径将使用 `/_/cos/getauthorization`）
  - 元数据生成：`CLOUDRUN_METAID_URL=<开放接口完整URL>` 或 `CLOUDRUN_OPEN_SERVICE_BASE=https://<服务域名>`（默认路径将使用 `/_/cos/metaid/encode`）

- 上传接口调用（需携带用户 `openid`）

```
curl -X POST \
  -H "x-wx-openid: <用户openid>" \
  -F "file=@/path/to/local.png" \
  https://<服务域名>/api/storage/upload
```

- 响应示例（开启元数据时返回 `metaid`，并写入 `x-cos-meta-fileid`）

```json
{
  "code": 0,
  "data": {
    "key": "uploads/20250101/<uuid>-local.png",
    "url": "https://<bucket>.cos.<region>.myqcloud.com/uploads/20250101/<uuid>-local.png",
    "metaid": "k1Z..."  
  }
}
```

- 获取 STS 临时秘钥：通过云托管开放接口服务（“获取临时秘钥”）即可，无需永久密钥。
  - 若配置动态拉取（`CLOUDRUN_STS_URL` 或 `CLOUDRUN_OPEN_SERVICE_BASE`），后端会自动缓存并续期（过期前 60s 刷新）。
  - 若未配置 `CLOUDRUN_METAID_URL`/`CLOUDRUN_OPEN_SERVICE_BASE` 或未携带 `openid`，上传仍可成功，但不会写入 `x-cos-meta-fileid`。


## 数据库表结构（DDL）
- 位置：`docs/db-ddl.sql`
- 说明：默认创建并使用数据库 `flask_demo`；如需自定义库名，请修改文件开头的 `USE` 语句为你的 `MYSQL_DBNAME`。

### 本地执行示例（Windows）
- 使用命令行导入（需安装 `mysql` 客户端）：
  - `mysql -h127.0.0.1 -P3306 -uroot -p < docs\db-ddl.sql`
  - 将主机、端口、用户名按你的本地 MySQL 实际配置替换。

### 云托管 MySQL（控制台）
- 进入云托管的 MySQL 控制台，选择对应数据库，使用「导入 SQL 文件」或控制台查询窗口执行 `docs/db-ddl.sql` 的内容。
- 与环境变量一致后，后端可通过 `GET /api/db/health` 验证连接：
  - `curl http(s)://<服务域名>/api/db/health`



## License

[MIT](./LICENSE)
