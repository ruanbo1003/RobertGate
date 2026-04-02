# API: 相册

基础路径：`/api/v1/gallery`

---

## 1. 获取照片列表

**GET** `/api/v1/gallery/photos`

### 响应

成功：
```json
{
  "code": 0,
  "data": {
    "photos": [
      {
        "filename": "IMG_001.jpg",
        "url": "/photos/IMG_001.jpg",
        "width": 4032,
        "height": 3024
      }
    ],
    "total": 150
  },
  "message": "ok"
}
```

失败：
| code | message | 说明 |
|------|---------|------|
| 5001 | 照片目录不存在 | 服务器配置的目录路径无效 |
| 5002 | 照片目录读取失败 | 权限不足或 IO 错误 |

### 说明
- 读取服务器写死目录 `/home/ubuntu/photos` 下的所有图片文件
- 支持格式：jpg、jpeg、png、webp、gif
- 返回每张照片的文件名、静态 URL、宽高（像素）
- 照片按文件修改时间倒序排列（最新在前）
- 照片文件通过 Nginx 静态服务提供，URL 格式：`/photos/{filename}`
