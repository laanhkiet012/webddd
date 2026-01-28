# Golike Ultimate Dashboard

## 🌐 Cách hoạt động

```
┌─────────────────────────────┐      ┌──────────────────────────────┐
│  Vercel (Remote)            │      │  Máy người dùng (Local)      │
│  - Host giao diện UI        │ ◀──▶ │  - Chạy server.js            │
│  - Không xử lý API          │      │  - Gọi API Golike/IG/Pin     │
└─────────────────────────────┘      └──────────────────────────────┘
```

## 🚀 Deploy lên Vercel

1. **Push code lên GitHub**
```bash
git add .
git commit -m "Update for Vercel"
git push origin main
```

2. **Import project trên Vercel**
- Vào https://vercel.com/new
- Import repo từ GitHub
- Click Deploy

## 💻 Người dùng chạy tool

Sau khi deploy xong, người dùng cần:

1. **Cài Node.js** trên máy: https://nodejs.org/

2. **Tải code về máy:**
```bash
git clone [URL repo]
cd golike-ultimate-dashboard
npm install
```

3. **Chạy backend:**
```bash
node server.js
```

4. **Mở web trên Vercel** và sử dụng bình thường

## ⚠️ Lưu ý quan trọng

- **Người dùng PHẢI chạy `server.js`** trên máy của họ
- Web chỉ là giao diện - backend chạy local để tránh rate limit
- Không cần VPS mạnh - mọi xử lý diễn ra trên máy người dùng
