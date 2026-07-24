# Chuyển Cena Checker sang Oracle Cloud (miễn phí vĩnh viễn)

Hướng dẫn dựng web trên VM Oracle Always Free, tự cấp HTTPS, và **tự động deploy
mỗi khi push GitHub** (giống Railway). Làm 1 lần, sau đó không phải đụng tới nữa.

---

## A. Tạo VM Oracle Always Free

1. Đăng ký **cloud.oracle.com** (cần thẻ để xác minh — Always Free **không bị trừ tiền**).
2. Menu → **Compute → Instances → Create Instance**:
   - **Image**: Canonical **Ubuntu 22.04**.
   - **Shape**: bấm *Change shape* → chọn **VM.Standard.A1.Flex** (ARM, Always Free, để 1 OCPU / 6 GB là đủ).
     - Nếu báo *Out of capacity* → đổi sang **VM.Standard.E2.1.Micro** (AMD, luôn có).
   - **SSH keys**: *Generate a key pair* → **tải private key về máy** (giữ kỹ), hoặc dán public key của bạn.
   - Bấm **Create**. Đợi tới khi *Running*, ghi lại **Public IP address**.
3. Mở firewall của Oracle:
   - Vào instance → **Virtual Cloud Network** → **Security Lists** → *Default Security List*.
   - **Add Ingress Rules** (thêm 2 rule):
     - Source `0.0.0.0/0`, IP Protocol **TCP**, Destination Port **80**.
     - Source `0.0.0.0/0`, IP Protocol **TCP**, Destination Port **443**.

## B. DuckDNS (tên miền miễn phí)

1. Vào **duckdns.org** → đăng nhập (Google/GitHub).
2. Gõ tên subdomain muốn dùng (vd `cena-checker`) → **add domain**.
   Bạn sẽ có `cena-checker.duckdns.org`.
3. Ở ô **current ip**, điền **Public IP** của VM Oracle → **update ip**.
4. Copy **token** (chuỗi dài ở đầu trang) — cần cho bước sau.

## C. Cài đặt — chỉ 1 lệnh

SSH vào VM (Windows dùng PowerShell):
```
ssh -i duong-dan-private-key ubuntu@<PUBLIC-IP>
```
Rồi chạy (thay domain + token của bạn):
```
git clone https://github.com/my-tools26/cena-checker.git \
  && cd cena-checker \
  && sudo bash deploy/bootstrap.sh cena-checker.duckdns.org <DUCKDNS-TOKEN>
```
Đợi ~30 giây cho Caddy xin chứng chỉ HTTPS. Xong!

→ Mở **https://cena-checker.duckdns.org** — web chạy, ổ khóa xanh, camera quét mã vạch hoạt động.

## D. Từ đó về sau — TỰ ĐỘNG

- Mọi `git push` lên GitHub (kể cả các task cào giá tự động) → trong **≤ 2 phút**
  VM tự `git pull` + khởi động lại. **Bạn không phải làm gì.**
- Reboot VM → web tự chạy lại.

---

## Kiểm tra / xử lý sự cố

```bash
# 3 service phải đều active
systemctl status cena caddy cena-autodeploy.timer

# xem log auto-deploy
tail -f ~/cena-checker/deploy/autodeploy.log

# xem log web
journalctl -u cena -f

# nếu HTTPS chưa lên: xem log Caddy
journalctl -u caddy -f
```

- **Web không mở được**: kiểm tra đã thêm Ingress Rule 80/443 ở bước A.3 chưa.
- **HTTPS báo lỗi cert**: DuckDNS phải trỏ đúng IP VM (bước B.3); đợi thêm 1-2 phút.
- **Đổi sang domain riêng sau này**: sửa `/etc/caddy/Caddyfile` thay domain →
  `sudo systemctl reload caddy`.

## Ghi chú

- Railway vẫn chạy song song tới khi bạn hài lòng với Oracle. Cả hai deploy chung
  từ nhánh `master` — không xung đột. Muốn bỏ Railway thì xóa project bên đó.
- Các task cào giá **vẫn chạy trên máy Windows** của bạn (Claude Code) rồi push
  GitHub — Oracle chỉ phục vụ trang.
