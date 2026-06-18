# Migration Plan — แยก Design System ออกจาก DesignOps

> เป้าหมาย: 2 repo + 1 product repo ตาม concept 8 ข้อ
> หลักการ: **ย้ายไฟล์ = ง่าย, สร้าง seam = ยาก**. แผนนี้ทำ seam ก่อนเสมอ แล้วค่อยย้าย

## สถานะปัจจุบัน (ของจริงใน repo)

| สิ่งที่ต้องแก้ | ที่อยู่ตอนนี้ | ปัญหา |
|---|---|---|
| DS ถูก **copy** เข้า prototype | `scripts/setup-prototype.sh:61-69` (`rsync ... "$DS"/ "$PROTO"/`) | นี่คือ "Copy DS" ที่ข้อ 5 ต้องล้ม |
| DS เป็น **app** ไม่ใช่ package | `design-system/package.json` (`"private": true`, ไม่มี `exports`) | `npm install` ไม่ได้ |
| Internal import `@/lib/utils` | 49 จุดใน `design-system/components/ui/*` | `@/` resolve ไม่ได้เมื่อเป็น package |
| Token เป็น CSS-first | `design-system/app/globals.css` (Tailwind v4 `@theme`) | กระจายแยกไม่ได้ถ้าไม่แตก preset |
| brand.config สร้างโดย DesignOps | `run_pipeline.sh:293` | ข้อ 6 ต้องให้ไปอยู่ product repo |
| Validation ฝัง output | `scripts/audit_prototype.py` อ่าน `prototype/.../globals.css` ตรงๆ | ต้อง resolve token ข้าม repo |

---

## Phase 0 — Freeze & Inventory (0.5 วัน)

**ทำ:**
- `git tag pre-ds-split` บน repo ปัจจุบัน (จุด rollback)
- เขียน inventory: นับ component ที่ใช้ `@/` import, list token ทั้งหมดใน `globals.css`, list ทุกจุดที่ pipeline แตะ `design-system/`
- ตัดสินใจ distribution model (ดู Phase 3): **แนะนำ npm package + git tag version** เริ่มต้น (เปลี่ยนเป็น registry ภายหลังได้)

**Exit:** มี tag + inventory เอกสาร
**Rollback:** —
**Risk:** ต่ำ

---

## Phase 1 — สร้าง Contract Layer (สำคัญสุด — แก้ข้อ 8) (2-3 วัน)

> ทำ **ในrepo ปัจจุบันก่อน** ขณะที่ทุกอย่างยังอยู่ที่เดิม จะ refactor ปลอดภัยกว่าการย้ายไปพร้อมแก้
> รายละเอียดเต็ม: [`CONTRACT-AND-BOUNDARY.md`](./CONTRACT-AND-BOUNDARY.md)

**ทำ:**
1. นิยาม `generated/` (DesignOps เขียน) vs `src/` (dev เท่านั้น) boundary ในรูปแบบ scaffold
2. สร้าง **component contract** (prop schema ของ 52 component) + **token contract** (token names + roles) + **screen contract** (blueprint schema)
3. ใส่ codegen markers + CI guard ที่บล็อกการเขียนทับนอก `generated/`

**Exit:** มี contract artifact + CI guard ที่พิสูจน์ได้ว่า regenerate ไม่แตะ `src/`
**Rollback:** ลบ `generated/` boundary — ไม่กระทบ DS
**Risk:** 🔴 สูง — ถ้า seam ไม่แน่น ข้อ 8 บังคับไม่ได้. **อย่าข้าม phase นี้ไปย้ายไฟล์ก่อน**

---

## Phase 2 — แตก DS เป็น repo แยก (1-2 วัน)

**ทำ:**
- สร้าง repo `design-system` ใหม่ ย้าย: `components/`, `lib/`, `hooks/`, `app/globals.css`(→ `tokens.css`), Storybook, Contract (จาก Phase 1)
- **ทิ้งส่วน app**: `app/page.tsx`, `app/layout.tsx`, `next.config.ts` (เก็บเฉพาะ Storybook/preview harness)
- DesignOps repo เก็บ: `references/aesthetics/` (138 systems), `references/intelligence-layer.md`, validation scripts, research/competitor/domain → **ส่วนใหญ่อยู่แล้ว** (`.claude/skills/designops-pipeline/`)

**Exit:** 2 repo แยกกัน DS มีแต่ library surface
**Rollback:** ยังไม่ลบของเดิมจนกว่า Phase 3 ผ่าน
**Risk:** 🟡 ปานกลาง — git history ของ DS หาย ถ้าไม่ใช้ `git filter-repo`

---

## Phase 3 — ทำ DS ให้ import ได้ + เลิก copy (แก้ข้อ 5) (2-3 วัน)

> PoC พิสูจน์กลไกนี้แล้ว: [`poc/`](./poc/) — รัน `bash poc/verify.sh`

**ทำ:**
1. `package.json`: `name @acme/ds`, `exports` map, `peerDependencies` (react/radix/lucide), เลิก `"private": true`
2. แก้ internal import: `@/lib/utils` → Node subpath imports `#lib/utils` (`"imports"` field) — แก้ครั้งเดียวด้วย codemod, build-time resolve ผ่าน tsup/tsc
3. **Token distribution**: export `tokens.css` (preset) + ใน product `@import "@acme/ds/tokens.css"` และ `@source "../node_modules/@acme/ds"` (Tailwind v4 ต้อง scan class ใน package)
4. แทน `setup-prototype.sh` rsync → `npm install @acme/ds@<version>` ใน scaffold
5. **Versioning**: semver + lockfile ใน product repo

**Exit:** product `npm install` DS ได้ + Tailwind เห็น class + token apply ถูก
**Rollback:** กลับไปใช้ rsync ชั่วคราว (เก็บ branch เดิมไว้)
**Risk:** 🔴 สูง — shadcn ออกแบบมาให้ "copy" ไม่ใช่ "import"; RSC + `"use client"` + Tailwind v4 scan เป็นจุดที่พังบ่อย. **Version skew**: product pin DS เก่า แต่ audit ด้วย token ใหม่ → ผลไม่ตรง (แก้ที่ Phase 5)

---

## Phase 4 — เปลี่ยน Output เป็น Blueprint + Scaffold (แก้ข้อ 4, 6, 7) (2 วัน)

**ทำ:**
- DesignOps เลิก emit prototype เต็ม → emit:
  - **Product Blueprint**: screen contract + flow + data shape (JSON/MD ใน `generated/`)
  - **Product Scaffold**: โครง repo ที่ `import @acme/ds`, มี `generated/` + `src/` (ว่างให้ dev เติม)
- ย้าย `brand.config.json` generation จาก DesignOps → ใส่ใน scaffold ที่ product repo (ข้อ 6) เป็นค่าเริ่มต้นให้ dev แก้
- กำหนด `CODEOWNERS`: `src/` = dev team (ข้อ 7), `generated/` = designops bot

**Exit:** DesignOps run → ได้ Blueprint + Scaffold (ไม่ใช่ prototype)
**Rollback:** flag `--legacy-prototype` เก็บ flow เดิมไว้
**Risk:** 🟡 ปานกลาง — งานออกแบบ artifact ไม่ใช่งานเทคนิคยาก

---

## Phase 5 — Cross-repo Validation (แก้ข้อ 3 + ปิดช่อง Phase 3/4) (1-2 วัน)

**ทำ:**
- Package validators (`audit_prototype.py`, `lint_hardcodes.py`, contrast) เป็น CLI ที่ product repo รันใน CI
- Audit ต้อง resolve token จาก **DS เวอร์ชันที่ติดตั้งจริง + brand.config ของ product** ไม่ใช่ไฟล์ในrepo DesignOps
- brand.config gate: pre-commit/CI ใน product repo เพราะ dev แก้ได้ (ปิดช่อง contrast ตก WCAG หลุด — ข้อ 6 risk)

**Exit:** product CI fail ถ้า brand/blueprint ละเมิด WCAG/token
**Rollback:** validation เป็น warning ก่อน enforce
**Risk:** 🟠 — CI ข้าม repo + resolve token เวอร์ชันถูกต้อง

---

## Phase 6 — Governance: Regenerate-by-PR (แก้ข้อ 7+8 ชนกัน) (1 วัน)

**ทำ:**
- DesignOps regenerate = **เปิด PR** ไป product repo (ไม่ push ตรง branch) — แก้เฉพาะ `generated/`
- CI guard บล็อก PR ที่ DesignOps แตะ `src/`
- dev review + merge

**Exit:** regenerate ผ่าน PR เท่านั้น, `src/` แตะไม่ได้โดย bot
**Risk:** 🟢 ต่ำ

---

## ลำดับวิกฤต (อย่าสลับ)

```
Phase 1 (Contract/seam) ──▶ Phase 3 (import) ──▶ Phase 5 (cross-repo validation)
        │ ข้อ 8                  │ ข้อ 5                │ ปิดช่องโหว่
        └── ถ้าข้ามอันนี้ ข้อ 8 เป็นแค่คำสัญญา บังคับไม่ได้
```

ความเสี่ยงรวมกระจุกที่ **Phase 1 (seam ของข้อ 8)** และ **Phase 3 (import ของข้อ 5)** — สองอันนี้คือ "ทำหรือพัง" ของทั้งโปรเจกต์
