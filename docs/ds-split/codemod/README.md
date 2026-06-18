# Codemod — `@/` → `#` (Phase 3, step 2)

ทำให้ DS import ได้แบบ package: แปลง internal alias `@/...` (tsconfig path) เป็น Node subpath import `#...` (package.json `imports`). เพราะ `@/` resolve ได้เฉพาะตอน DS ถูก **copy** เข้า app root — พอ **import** เป็น package มันชี้ไม่ถูก

## ใช้

```bash
bash codemod.sh <design-system-dir>           # แก้ไฟล์ + patch package.json/tsconfig
node verify-codemod.mjs <design-system-dir>   # พิสูจน์ว่าครบ + ไม่มี import ค้าง
```

idempotent — รันซ้ำได้. ของจริงให้รันบน branch แล้ว review diff

## ผลที่รันกับ DS จริง (ยืนยันแล้ว)

รันบน working copy ของ `design-system/` (76 ไฟล์ ts/tsx/mts):

```
PASS  no `@/` specifiers remain (found 0)
PASS  rewrote 169 specifiers to `#`
PASS  every `#` specifier resolves to a real file (0 dangling)
PASS  imports map covers every prefix used (#components, #lib, #hooks)
✅ CODEMOD VERIFIED on the real DS
```

ตัวอย่างผลจริง (`components/ui/button.tsx`):
```diff
- import { cn } from "@/lib/utils"
+ import { cn } from "#lib/utils"
```

patch ที่ใส่ให้อัตโนมัติ:
```jsonc
// package.json
"imports": { "#lib/*": "./lib/*", "#components/*": "./components/*", "#hooks/*": "./hooks/*" }
// tsconfig.json  → compilerOptions.paths mirror เดียวกัน
```

## Build จริงผ่านครบ chain (ยืนยันแล้ว)

หลัง codemod + `npm install` (741 packages) บนสำเนา DS จริง:

```
✓ tsc --noEmit            exit 0 (ไม่มี error)
✓ next build (Turbopack)  ✓ Compiled successfully + Finished TypeScript
✓ static generation       65/65 pages (ทุก /docs/* route)
build exit 0
```

→ Turbopack resolve `#` subpath ครบทุกตัวในการ build จริง ไม่ใช่แค่ type-check
(รอบแรก build fail ที่ `/docs/colors` เพราะตอน copy ผม `--exclude .claude` ทำให้ขาดไฟล์ asset 926KB — ไม่เกี่ยวกับ codemod; เติมกลับแล้ว build เขียว)

## ขอบเขต / สิ่งที่ต้องทำต่อ

- **ปลอดภัยเพราะ** DS ไม่มี `@/` นอก import specifier เลย (ตรวจแล้ว) → `perl` replace `"@/`→`"#` ไม่โดน comment/css
- รันบน `/tmp/ds-codemod-real` เท่านั้น — **`design-system/` ตัวจริงไม่ถูกแตะ** (pipeline ปัจจุบันยังทำงานปกติ)
- ขั้นนี้พิสูจน์ว่า DS **ยัง build เป็น app ได้** หลัง codemod. ขั้น Phase 3 ที่เหลือคือทำเป็น *package* จริง: ใส่ `exports`/`peerDependencies`, build ด้วย tsup, publish version
- Tailwind v4: ฝั่ง product ต้อง `@source "../node_modules/@acme/ds"` เพื่อให้ scan class (อยู่นอกขอบเขต codemod นี้)
- `setup-prototype.sh:61-69` (rsync copy) เปลี่ยนเป็น `npm install` ในขั้นเดียวกัน
