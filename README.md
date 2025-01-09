# Hệ Thống Điểm Danh Bằng Nhận Diện Gương Mặt

## Tổng Quan
Dự án này là một **Hệ Thống Điểm Danh Bằng Nhận Diện Gương Mặt**, sử dụng **OpenCV** để nhận diện khuôn mặt, **PyQt5** để xây dựng giao diện người dùng, và **PostgreSQL** làm cơ sở dữ liệu. Ứng dụng được container hóa bằng **Docker** để dễ dàng triển khai và mở rộng.

## Tính Năng
- Nhận diện khuôn mặt thời gian thực để điểm danh.
- Giao diện thân thiện với người dùng được xây dựng bằng **PyQt5**.
- Lưu trữ dữ liệu an toàn và hiệu quả với **PostgreSQL**.
- Được container hóa hoàn toàn bằng **Docker** để đảm bảo tính nhất quán và dễ dàng triển khai.
- Tải danh sách học sinh theo lớp và ngày đã chọn
- Hiển thị trạng thái điểm danh hiện tại nếu đã có
- Cho phép cập nhật hàng loạt
- Tự động refresh danh sách học sinh khi lưu điểm danh

## Yêu Cầu
- Docker & Docker Compose
- Python
- PostgreSQL

## Cài Đặt

1. **Clone Repository:**
   ```bash
   git clone https://github.com/yourusername/facial-recognition-attendance.git
   cd opencv2
   ```

2. **Thiết Lập Biến Môi Trường:**
   Tạo file `.env` trong thư mục gốc của dự án với nội dung sau:
   ```env
   POSTGRES_USER=tên_người_dùng
   POSTGRES_PASSWORD=mật_khẩu
   POSTGRES_DB=attendance_db
   ```

3. **Xây Dựng Và Chạy Docker Containers:**
   ```bash
   docker-compose up --build
   ```

4. **Truy Cập Ứng Dụng:**
   - Ứng dụng PyQt5 có thể được khởi chạy bằng cách chạy script chính bên trong container:
     ```bash
     docker exec -it recognition_app python app.py
     ```

## Công Nghệ Sử Dụng
- **OpenCV:** Xử lý nhận diện khuôn mặt.
- **PyQt5:** Tạo giao diện đồ họa người dùng.
- **PostgreSQL:** Lưu trữ dữ liệu điểm danh.
- **Docker:** Container hóa và dễ dàng triển khai.

## Sử Dụng
1. **Đăng Ký Khuôn Mặt:**
   - Sử dụng giao diện PyQt5 để đăng ký các khuôn mặt mới vào hệ thống.
   
2. **Bắt Đầu Điểm Danh:**
   - Khởi chạy ứng dụng và cho phép xử lý video thời gian thực để nhận diện khuôn mặt.

3. **Xem Nhật Ký Điểm Danh:**
   - Dữ liệu điểm danh được lưu trữ trong cơ sở dữ liệu PostgreSQL và có thể được truy vấn hoặc xuất ra khi cần.


## About the Author

**Name:** Võ Phi Hùng  
**Email:** [vophihung987@gmail.com](mailto:vophihung987@gmail.com)  
**GitHub:** [github.com/phihungvo](https://github.com/phihungvo)  
