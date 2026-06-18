// Composition root: wires the GENERATED screen shell to the DEV-OWNED binding.
// Proves the two halves interoperate across the contract seam.
import { createBookingScreen } from "./generated/screens/booking.mjs";
import { bookingActions } from "./src/bindings/booking.mjs";

const screen = createBookingScreen({ actions: bookingActions });
const result = await screen.submit({ nights: 3, rate: 100, roomId: "R1" });

// machine-readable line the verify script parses (layout = generated, total = dev logic)
console.log(JSON.stringify({ layout: screen.layout, total: result.total, id: result.id }));
