# DS → importable package (tsup build) — Phase 3, step 3

แปลง design system (ที่ codemod `@/`→`#` แล้ว) เป็น npm package ที่ product repo **import** ได้ (ข้อ 5) — เลิก rsync copy

## ทำไม config เป็นแบบนี้

| ทางเลือก | เหตุผล |
|---|---|
| `bundle: false` (transpile-only) | shadcn เป็น component แยกไฟล์ + มี `"use client"` 43 ไฟล์ — bundle รวมจะทำ directive พังและ tree-shaking เสีย |
| `esbuild-plugin-preserve-directives` | esbuild ตัด `"use client"` ทิ้งตอน transform — plugin ดึงกลับมาไว้ **บรรทัด 1** (Next ต้องการตำแหน่งนี้เป๊ะ) |
| d.ts ด้วย `tsc` แยก (ไม่ใช่ `dts:true` ของ tsup) | tsup dts (rollup) resolve `#` subpath ไม่ครบ — `tsc` อ่าน `paths` ใน tsconfig ตรงๆ |
| `type: "module"` → output `.js` | ให้ `.js` คู่กับ `.d.ts` พอดี (เลี่ยงปัญหา `.mjs`/`.d.mts` mismatch) |
| subpath exports `./*` (ไม่มี barrel) | `import { Button } from "@acme/ds/button"` — tree-shakeable, ไม่มี name collision จาก 52 component |
| `imports` map → `./dist/*.js` | internal `#lib/utils` (จาก codemod) resolve ที่ runtime ไปไฟล์ที่ build แล้ว |

## ใช้

```bash
bash ../codemod/codemod.sh <ds-dir>      # ต้องทำก่อน
bash build.sh <ds-dir>                   # tsup + tsc → dist/
# merge package.recipe.json เข้า package.json ของ DS แล้ว:
cd <ds-dir> && npm pack                   # → tarball พร้อม publish
```

## ผลที่รันจริง (ยืนยันแล้ว end-to-end)

build บน DS จริง (52 component + lib + hooks):

```
tsup        ✓ 55 .js  ("use client" คงอยู่บรรทัด 1 ครบทุก client component)
tsc         ✓ 55 .d.ts (type เต็ม เช่น Button + buttonVariants variants)
#-imports   ✓ คงในไฟล์ที่ build (#lib/utils ×49 …) resolve ผ่าน imports map
npm pack    ✓ acme-ds-1.0.0.tgz — มีแต่ dist/ + globals.css, 0 .tsx source leak
```

consumer ใหม่ install tarball (136 packages จาก deps ของ package เอง) แล้ว:

```tsx
import { Button } from "@acme/ds/button";
import { cn } from "@acme/ds/lib/utils";
import { useIsMobile } from "@acme/ds/hooks/use-mobile";
```
```
tsc --noEmit       TYPECHECK_EXIT=0   (types ผ่าน exports + internal # ของ package)
node import button  RUNTIME_EXIT=0     (buttonVariants() รัน = #lib/utils resolve runtime)
```

## ที่ยังเหลือ (นอกขอบเขต step นี้)

- **Tailwind v4**: product ต้อง `@import "@acme/ds/globals.css"` + `@source "../node_modules/@acme/ds/dist"` ให้ scan class ของ component (class เป็น string ใน .js — Tailwind ต้องเห็น)
- peerDependencies จริงควรรวม radix/lucide/cva ด้วย (ตอนนี้ทำเป็น dependencies เพื่อให้ PoC install ครบในขั้นเดียว)
- publish ไป registry/GitHub Packages + version pin ใน product lockfile
- `setup-prototype.sh:61-69` (rsync) → `npm install @acme/ds@<ver>`
