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
```
## 🚀 Cập nhật thiết bị
### `PUT /devices/{id}`
Cập nhật thông tin của một thiết bị dựa trên ID.

#### Request
- **`id`** (str): ID của thiết bị cần cập nhật.
- **`value`** (int/str): Giá trị mới của thiết bị.
- **`status`** (str, optional): Trạng thái thiết bị (`on` hoặc `off`).

#### Response
- **200 OK**: Thiết bị được cập nhật thành công.
- **404 Not Found**: Không tìm thấy thiết bị.

#### Cách hoạt động
1. Kiểm tra nếu thiết bị tồn tại.
2. Gửi lệnh cập nhật giá trị thiết bị thông qua hàng đợi (`send_queue`).
3. Phát sự kiện WebSocket cập nhật giá trị của thiết bị.
4. Nếu `status` chưa được đặt hoặc là `"off"`, sẽ được kiểm tra dựa trên `value`.
5. Lưu cập nhật vào cơ sở dữ liệu và phản hồi kết quả.

---

## 🔄 Bật/Tắt thiết bị
### `PATCH /devices/{id}`
Chuyển đổi trạng thái của một thiết bị.

#### Request
- **`id`** (str): ID của thiết bị cần thay đổi trạng thái.

#### Response
- **200 OK**: Trạng thái thiết bị đã được thay đổi thành công.
- **404 Not Found**: Không tìm thấy thiết bị.
- **410 Gone**: Thiết bị là cảm biến, không thể bật/tắt.

#### Cách hoạt động
1. Kiểm tra nếu thiết bị tồn tại.
2. Kiểm tra nếu thiết bị là cảm biến (`sensor`), nếu đúng thì từ chối thay đổi.
3. Đổi trạng thái (`on` ⇄ `off`) cho thiết bị.
4. Cập nhật giá trị của thiết bị dựa trên trạng thái:
   - `door`: `"ON"` hoặc `"OFF"`
   - `fan`: `100` hoặc `0`
   - `light`: `1` hoặc `0`
5. Phát sự kiện WebSocket thông báo thay đổi trạng thái thiết bị.
6. Nếu là `fan`, gửi sự kiện cập nhật giá trị thông qua WebSocket.
7. Lưu trạng thái mới vào cơ sở dữ liệu và phản hồi kết quả.

---
# API Cameras

## 1. Lấy danh sách tất cả người dùng
### `GET /all_users`
Trả về danh sách ID của tất cả người dùng.

#### Response
- **200 OK**: Danh sách tất cả ID người dùng.

---

## 2. Đăng ký khuôn mặt
### `POST /register_face`
Thêm embedding của khuôn mặt vào danh sách của người dùng.

#### Request
- **`user_id`** (str): ID của người dùng.
- **`image_base64`** (str): Dữ liệu hình ảnh được mã hóa base64.

#### Response
- **201 Created**: Đăng ký khuôn mặt thành công.
- **400 Bad Request**: Dữ liệu hình ảnh hoặc ID không hợp lệ.
- **500 Internal Server Error**: Lỗi xử lý hình ảnh hoặc lưu trữ embedding.

---

## 3. Xác thực khuôn mặt
### `POST /verify_face`
Xác thực khuôn mặt với ID người dùng đã đăng ký để quyết định mở cửa hay không.

#### Request
- **`camera_verify_id`** (str): ID của camera.
- **`image_base64_to_check`** (str): Dữ liệu hình ảnh cần kiểm tra.

#### Response
- **200 OK**: Xác thực thành công.
- **400 Bad Request**: Dữ liệu hình ảnh hoặc ID không hợp lệ.
- **404 Not Found**: Không tìm thấy user ID đăng ký hoặc không có embedding.
- **500 Internal Server Error**: Lỗi xử lý hình ảnh.

---

## 4. Cập nhật thông tin camera
### `PUT /{id}`
Cập nhật danh sách user ID đã đăng ký của camera.

#### Request
- **`id`** (str): ID của camera.
- **`user_id`** (str): ID người dùng cần cập nhật.
- **`delete`** (bool, tùy chọn): Xóa người dùng khỏi danh sách nếu `true`.

#### Response
- **200 OK**: Cập nhật thành công.
- **400 Bad Request**: Người dùng đã đăng ký hoặc chưa có trong danh sách.
- **404 Not Found**: Không tìm thấy camera hoặc user ID.

---

## 5. Bật/tắt camera
### `PATCH /{id}`
Chuyển đổi trạng thái hoạt động của camera.

#### Request
- **`id`** (str): ID của camera.

#### Response
- **200 OK**: Trạng thái của camera đã được cập nhật.
- **404 Not Found**: Không tìm thấy camera.

---
# API Voice

## 1. Lấy bản ghi giọng nói
### `GET /transcript`
Ghi âm và chuyển thành văn bản.

#### Response
- **200 OK**: Trả về nội dung giọng nói đã chuyển thành văn bản.
- **400 Bad Request**: Lỗi xử lý giọng nói.
- **500 Internal Server Error**: Lỗi ghi âm giọng nói.

---

## 2. Xử lý lệnh bằng giọng nói
### `POST /voice_logic`
Xử lý logic từ lệnh giọng nói để kiểm soát các thiết bị.

#### Request
- **`request`** (str): Lệnh giọng nói cần xử lý.

#### Response
- **200 OK**: Thành công.
- **404 Not Found**: Lệnh giọng nói không hợp lệ hoặc không thể xử lý.

---

### **Cách hoạt động**
1. **Xác định các thiết bị được điều khiển**  
   - `light` (đèn), `fan` (quạt), `door` (cửa), `camera` (xác thực khuôn mặt).
   - Các trạng thái: `TURN_ON`, `TURN_OFF`, `OPEN`, `CLOSE`.

2. **Xác định điều kiện thực hiện**  
   - Cảm biến `temperature`, `humidity`, `light`.
   - Cảm biến `fan` để điều chỉnh tốc độ.
   - `time_delay`: khoảng thời gian chờ trước khi thực hiện lệnh.

3. **Thực hiện lệnh nếu điều kiện hợp lệ**  
   - Nếu `time_delay > 0`, lệnh sẽ được thực hiện sau khoảng thời gian này.
   - Nếu thiết bị thuộc nhóm (`light`, `fan`, `door`), trạng thái của thiết bị sẽ được cập nhật.
   - Nếu là `camera`, trạng thái xác thực khuôn mặt sẽ được thay đổi.

4. **Lưu lịch sử**  
   - Lưu lại yêu cầu và phản hồi vào hệ thống.

---
# WebSocket Environment

## 1. Lấy giá trị cảm biến
### `get_sensor_value(session, sensor_type)`
Hàm này truy vấn giá trị của cảm biến từ cơ sở dữ liệu.

#### Tham số
- **`session`**: Phiên làm việc với cơ sở dữ liệu.
- **`sensor_type`**: Loại cảm biến cần lấy giá trị (`temperature-sensor`, `humidity-sensor`, `light-sensor`).

#### Kết quả
- Giá trị của cảm biến nếu tìm thấy.
- `None` nếu cảm biến không tồn tại.

---

## 2. Cập nhật môi trường theo thời gian thực
### `WebSocket /environment`
WebSocket cung cấp cập nhật trực tiếp về các giá trị cảm biến nhiệt độ, độ ẩm và ánh sáng.

#### Quy trình hoạt động
1. **Kết nối WebSocket**  
   - WebSocket được thiết lập để liên tục nhận dữ liệu môi trường từ các cảm biến.
   
2. **Theo dõi và phát giá trị cảm biến**  
   - Cảm biến gồm: `temperature`, `humidity`, `light`.
   - Dữ liệu được gửi đi nếu có thay đổi và thỏa mãn khoảng thời gian `throttle_interval`.

3. **Điều chỉnh tần suất cập nhật**  
   - Dữ liệu chỉ được gửi khi có thay đổi so với giá trị trước đó.
   - Giới hạn tần suất phát dữ liệu (`throttle_interval = 2 giây`) để tránh quá tải.

4. **Ngắt kết nối**  
   - Khi WebSocket bị ngắt, hệ thống dừng cập nhật và đóng phiên làm việc với cơ sở dữ liệu.

---

## 3. Sự kiện được phát qua WebSocket
### Các sự kiện môi trường
| Sự kiện                    | Nội dung |
|----------------------------|---------|
| `environment:temperature`  | Truyền giá trị nhiệt độ từ cảm biến |
| `environment:humidity`     | Truyền giá trị độ ẩm từ cảm biến |
| `environment:light`        | Truyền giá trị ánh sáng từ cảm biến |

---

### **Ghi chú**
- Giá trị cảm biến sẽ liên tục được kiểm tra và phát đi nếu có sự thay đổi.
- Hệ thống sử dụng `asyncio.sleep(2)` để điều chỉnh chu kỳ cập nhật.
- Khi kết nối bị mất (`WebSocketDisconnect`), WebSocket sẽ tự động ngắt và phiên làm việc sẽ được đóng.

---

