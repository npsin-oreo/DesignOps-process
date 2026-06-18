# Boundary PoC — "regenerate the Blueprint, never rewrite logic" (ข้อ 8)

จาก `../CONTRACT-AND-BOUNDARY.md` (ออกแบบ) → PoC ที่ **รันได้จริง** พิสูจน์ว่า DesignOps regenerate
ทับ business logic ไม่ได้

```bash
bash verify.sh
```

ผล (ยืนยันแล้ว):
```
PASS  regenerate updated the generated screen (layout changed)
PASS  src/ unchanged after regenerate (hash identical)
PASS  business logic intact (total 321 == 321)
PASS  generated files marked @generated
PASS  guard blocks bot editing src/ → exit 1
PASS  guard allows bot editing generated/ → exit 0
✅ POINT 8 ENFORCED
```

## โครงสร้าง = seam 3 ชั้น

```
product/
  generated/                 ← DesignOps เขียนได้ 100% (regenerate ลบ+เขียนใหม่)
    blueprints/booking.blueprint.json   ← source of truth ของ design
    contracts/booking.mjs               ← @generated: assertBookingData + ACTIONS (seam)
    screens/booking.mjs                 ← @generated: UI shell, ไม่มี logic, delegate ไป actions
  src/                       ← Dev เท่านั้น (bot แตะไม่ได้)
    logic/pricing.mjs                   ← business logic (computeTotal + tax)
    bindings/booking.mjs                ← implement BookingActions ด้วย logic จริง
  app.mjs                    ← composition root: ต่อ generated screen × dev binding
  CODEOWNERS                 ← /generated→bot, /src→dev-team
regenerate.sh                ← เขียนเฉพาะ generated/** จาก blueprint
guard.sh                     ← CI: bot PR ที่แตะนอก generated/ → exit 1
```

## ทำไมมันบังคับได้ (ไม่ใช่แค่ "ตั้งใจ")

| กลไก | พิสูจน์อะไร |
|---|---|
| `regenerate.sh` เขียนเฉพาะ `generated/` | เปลี่ยน blueprint → screen เปลี่ยน, **src/ hash เท่าเดิม** |
| screen เป็น shell ที่ delegate ไป `actions` ผ่าน contract | logic อยู่ใน src/, regenerate ไม่แตะ → total เท่าเดิม |
| `guard.sh` + `CODEOWNERS` | bot แตะ src/ → CI fail; แตะ generated/ → ผ่าน |
| `@generated` marker | จับการแก้มือใน generated/ ได้ (ของจะถูกเขียนทับ) |

## ที่เหลือสำหรับของจริง
- regenerate เป็น 3-way/PR (Phase 6): bot เปิด PR แก้ generated/ ให้ dev review ไม่ push ตรง
- contract เป็น `.ts` จริง + type-check ข้าม generated↔src (ตอนนี้ใช้ runtime assert ให้รัน offline ได้)
- เดินหลายหน้าจาก blueprint หลายไฟล์ (PoC ทำ booking หน้าเดียว)
