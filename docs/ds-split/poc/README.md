# PoC — "Import the DS, don't copy it" (ข้อ 5)

รันได้จริง ไม่ต้องต่อเน็ต (ใช้ `file:` dependency):

```bash
bash verify.sh
```

ผลที่ได้ (ยืนยันแล้ว):
```
PASS  DS installed as dependency in node_modules (not copied)
PASS  product repo vendors no DS source of its own
PASS  component code runs (internal #lib/* resolved)
PASS  badgeClass() composes via DS internals
PASS  tokens.css distributed via export map
PASS  Button contract importable via subpath
✅ ALL PROOFS PASSED — import-not-copy works
```

## พิสูจน์อะไร

| Proof | ตอบโจทย์ปัญหาจริงข้อไหน |
|---|---|
| DS เป็น symlink ใน `node_modules`, consumer ไม่มี source ของ DS เลย | แทน `rsync` copy ใน `setup-prototype.sh:61-69` (ข้อ 5) |
| `#lib/*` subpath resolve ได้ | แก้ `@/lib/utils` 49 จุดที่ resolve ไม่ได้ตอนเป็น package |
| `tokens.css` มาทาง export map | Token CSS-first ใน `globals.css` กระจายเป็น preset ได้ |
| Button contract import ผ่าน subpath | seam ของข้อ 8 (ดู `../CONTRACT-AND-BOUNDARY.md`) |

## โครงสร้าง

```
packages/ds/          ← @acme/ds-poc  (= design-system repo ในอนาคต)
  package.json        ← exports + imports(#lib/*) + peerDependencies
  dist/index.js       ← re-export ผ่าน "#lib/utils" (internal subpath)
  dist/lib/utils.js   ← cn() (จริงใช้ clsx+twMerge; PoC ทำ dep-free เพื่อรัน offline)
  tokens.css          ← token preset
  contracts/*.json    ← component contract
consumer/             ← product repo (Dev = owner, ข้อ 7)
  package.json        ← "@acme/ds-poc": "file:../packages/ds"  ← IMPORT ไม่ copy
  app.mjs             ← = generated/screens/* ที่ import DS
```

## ข้อจำกัดของ PoC (ของจริงต้องเพิ่ม)

- ของจริง component เป็น `.tsx` + RSC + `"use client"` → ต้อง build ด้วย tsup/tsc, ใส่ react ใน `peerDependencies`
- Tailwind v4 ต้อง `@source "../node_modules/@acme/ds-poc"` ใน product ไม่งั้นไม่ scan class ของ DS
- `@/` → `#` ต้องใช้ codemod แก้ทีเดียว 49 จุด (build-time resolve)
- version: ของจริง publish เป็น registry/git tag + pin ใน product lockfile (ดู Phase 3)
