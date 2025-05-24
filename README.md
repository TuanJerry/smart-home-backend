# smart-home-backend
Back-end implemented by FastAPI for smart home app

Các API được xây dựng tương ứng như sau

## 📟 Devices API
API để quản lý các thiết bị trong hệ thống Smart Home, bao gồm tạo mới, lấy danh sách, cập nhật, bật/tắt và xóa thiết bị.
### 📌 Base URL
`/devices`
### 🚀 Endpoints
#### `GET /devices`
Lấy danh sách tất cả thiết bị, có thể lọc theo `roomId`.

- **Query Parameters:**
  - `skip` (int, optional): Số lượng thiết bị bỏ qua. Mặc định: `0`.
  - `limit` (int, optional): Giới hạn số lượng kết quả trả về. Mặc định: `100`.
  - `roomId` (UUID, optional): ID của phòng để lọc thiết bị.

- **Response:** `200 OK`

```json
[
  {
    "id": "string",
    "name": "string",
    "type": "fan | light | door | ...",
    "value": 100,
    "status": "on",
    ...
  }
]

