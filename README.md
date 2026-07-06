# 🛒 Cena Checker — So sánh giá siêu thị Séc cho người Việt

Tìm giá rẻ nhất bằng **tiếng Việt (có dấu hoặc không dấu)**: gõ "sữa tươi", "đùi gà", "gạo thơm"...
là ra bảng so sánh **bán lẻ** (Kaufland, Lidl, Billa, Penny, Tesco, Albert, Globus...)
và **bán buôn** (Tamda Foods, Makro, JIP) — kèm xếp hạng giá trên 1 kg / 1 lít / 1 quả.

## Tính năng

- 🔍 Tìm kiếm tiếng Việt → tự dịch sang tiếng Séc (từ điển ~670 mục, tự mở rộng được qua `tudien.xlsx`)
- 🏆 Xếp hạng rẻ nhất theo **giá đơn vị** (so được vỉ trứng 10 quả với vỉ 30 quả)
- 🅣 Tờ rơi **Tamda Foods** (số hóa thủ công hằng tuần) + Ⓜ Makro + 🄹 JIP trong cột bán buôn
- 🅃 Giá **Tesco online** gồm cả giá thẻ Clubcard
- ⏰ Gợi ý deal **sắp hết hạn hôm nay/ngày mai** + 🆕 deal tờ rơi mới, đổi mỗi lần F5
- 🍉🥕 Trang hoa quả & rau củ khuyến mãi tuần
- 🎟️ Coupon Lidl Plus cá nhân (chỉ bản chạy trên máy, đăng nhập bằng tài khoản của chính bạn)

## Cài đặt (Windows)

1. Cài [Python](https://www.python.org/downloads/) (tích "Add to PATH" khi cài)
2. Tải repo này về (Code → Download ZIP → giải nén)
3. Mở PowerShell trong thư mục, chạy: `pip install -r requirements.txt`
4. Nháy đúp **`CENA.bat`** — trình duyệt tự mở trang app
5. (Tùy chọn) Coupon Lidl Plus: nháy đúp `LIDL-DANGNHAP.bat`, đăng nhập tài khoản Lidl **của bạn**
   (cần Google Chrome; token lưu trên máy bạn, không chia sẻ đi đâu)

Dùng trên điện thoại cùng WiFi: mở địa chỉ mà cửa sổ đen hiển thị (dạng `http://192.168.x.x:8765`).

## Chạy bản công khai (hosting)

Đặt biến môi trường `CENA_PUBLIC=1` — app tự tắt tính năng coupon cá nhân và bật trang miễn trừ.
Lệnh chạy: `python app.py` (app tự đọc `PORT` từ môi trường nếu có).

## Miễn trừ trách nhiệm

Dữ liệu tổng hợp tự động từ nguồn công khai (kupi.cz, tờ rơi chính thức các chuỗi) — **chỉ mang
tính tham khảo**, giá thực tế tại cửa hàng có thể khác. Dự án cá nhân phi lợi nhuận, không liên
kết với Kupi.cz, Tamda Foods, Makro, Lidl, Tesco hay bất kỳ chuỗi nào. Vui lòng dùng điều độ,
không quét dồn dập các trang nguồn.
