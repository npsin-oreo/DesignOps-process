// DEV-OWNED business logic. The designops bot must never touch /src.
// This is the kind of code that regenerate would clobber if there were no boundary.
const TAX_RATE = 0.07;

export function computeTotal({ nights, rate }) {
  const subtotal = nights * rate;
  return Math.round(subtotal * (1 + TAX_RATE) * 100) / 100;
}
