# Publishing `@acme/ds` + wiring the pipeline to import it (Phase 3 finish)

ทุกอย่างก่อนหน้านี้พิสูจน์แล้ว (codemod → tsup build → peerDeps → token preset → Tailwind ใน Next จริง).
เหลือ **publish + สลับ pipeline ให้ import** — ขั้นนี้ต้องตัดสินใจ registry + credential

## 1. เลือก registry

| ตัวเลือก | เมื่อไหร่ | pin ใน product |
|---|---|---|
| **GitHub Packages** (แนะนำถ้า repo อยู่ GitHub) | private, ผูกกับ org เดียว | `.npmrc`: `@acme:registry=https://npm.pkg.github.com` |
| npm private registry | มี org บน npm อยู่แล้ว | `package.json` `"@acme/ds": "1.0.0"` |
| Git submodule / tarball | ยังไม่อยากตั้ง registry | `"@acme/ds": "github:org/ds#v1.0.0"` |

## 2. Build + publish (ใน DS repo)

```bash
bash codemod.sh <ds-dir>        # @/ → #   (ครั้งเดียว, commit)
bash build.sh   <ds-dir>        # tsup + tsc → dist/
# merge package.recipe.json เข้า package.json (exports/imports/peerDeps/files + ./tokens.css)
cd <ds-dir>
npm version 1.0.0
npm publish                     # หรือ npm publish --registry=https://npm.pkg.github.com
```

> **semver:** เปลี่ยน token/contract ที่ breaking → major. เพิ่ม component → minor. แก้ bug → patch.
> product **pin เวอร์ชัน** ใน lockfile → audit/contrast gate รันกับ token เวอร์ชันเดียวกับที่ใช้จริง (กัน version skew).

## 3. สลับ pipeline จาก copy → import

`setup-prototype.sh` รองรับแล้ว (rsync ยัง default — ไม่พังของเดิม):

```bash
# import mode (point 5): ติดตั้ง DS เป็น package แทน copy
bash setup-prototype.sh --out ./output --ds-import --ds-pkg @acme/ds@1.0.0
# tarball/path ต้องระบุชื่อ CSS ด้วย:
bash setup-prototype.sh --out ./output --ds-import --ds-pkg ./acme-ds-1.0.0.tgz --ds-name @acme/ds
```

import mode จะ: `npm install` DS package + react/react-dom, แล้วเขียน `app/globals.css`:
```css
@import "tailwindcss";
@import "@acme/ds/tokens.css";
@source "../node_modules/@acme/ds/dist";    /* gotcha #1 — ลืมแล้ว component ไม่มีสไตล์ */
```

พิสูจน์แล้ว (tarball): DS ลง `node_modules/@acme/ds` เป็น dependency, **0 .tsx source leak**, CSS wiring ถูกต้อง

## 4. ที่เหลือ (decision/credential ของคุณ)

- เลือก registry + ตั้ง `.npmrc` + token (CI secret)
- ตั้ง `prepublishOnly: "npm run build"` กัน publish ทั้งที่ลืม build
- (Phase 5) audit/contrast gate ของ product resolve token จาก `node_modules/@acme/ds` เวอร์ชันที่ pin + brand override
