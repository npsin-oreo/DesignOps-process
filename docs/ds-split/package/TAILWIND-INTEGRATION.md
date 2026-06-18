# Tailwind v4 integration — product ฝั่งที่ import DS เป็น package

Component import มาแล้ว (JS/types ผ่าน) **ยังไม่พอ** — Tailwind v4 ต้อง *scan class strings* ในไฟล์ที่ build เพื่อ gen CSS. node_modules ไม่ถูก scan โดย default → ต้องสั่ง `@source` เอง

## CSS entry ของ product (แนะนำ: token-only preset)

DS ship **`@acme/ds/tokens.css`** = token preset (`@theme` + `:root`/`.dark` + dark variant) ที่
**ไม่มี** framework import — product เป็นคน `@import "tailwindcss"` เอง (เลี่ยง double-import + ไม่ต้องลาก tw-animate/shadcn เป็น dep ของ DS)

```css
/* app/globals.css */
@import "tailwindcss";
@import "@acme/ds/tokens.css";              /* DS token preset (ไม่มี framework re-import) */
@source "../node_modules/@acme/ds/dist";    /* << บังคับให้ scan component ที่ build แล้ว */
```

## พิสูจน์แล้ว — Next.js 16 + Tailwind v4 PostCSS จริง (ไม่ใช่แค่ CLI)

product scaffold (`next build`) page ใช้แค่ `<Button>`/`<Card>` (ไม่มี raw tailwind class เอง):

```
✓ next build — 3/3 static pages
built CSS .next/static/chunks/*.css (121 KB):
  .inline-flex / .shrink-0 / .whitespace-nowrap   → มี (มาจาก @source scan dist)
  --primary (token)  → มี   ·   .dark variant → มี   (จาก tokens.css preset)
  .blur-3xl (ไม่มี component ใช้) → 0   (negative control)
```

→ utility ของ component เข้า built CSS ทั้งที่ page ไม่มี class เอง = `@source dist` ทำงานใน
Next/PostCSS pipeline จริง. **gotcha #1:** ลืม `@source dist` → component มีโครงแต่ไม่มีสไตล์ →
scaffold ที่ DesignOps สร้าง (Phase 4) ต้องใส่บรรทัดนี้เป็น default เสมอ

## สถานะ publish (อัปเดต)

- ✅ **token preset แยกแล้ว** → `tokens.css` (framework-agnostic) ship ผ่าน `exports["./tokens.css"]`. DS ไม่ต้องลาก tw-animate/shadcn เป็น dep อีก (เหลือไว้เฉพาะ `globals.css` แบบเดิมสำหรับ all-in-one)
- ✅ **peerDependencies จริงแล้ว** → react, react-dom, **radix-ui, lucide-react, class-variance-authority** (auto-install ในconsumer บน npm 7+; tsc + runtime ยัง EXIT 0)
- ⬜ publish ไป registry/GitHub Packages + version pin (ต้องเลือก registry + credential)
