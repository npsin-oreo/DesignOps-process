// DEV-OWNED binding. Implements the generated BookingActions contract with real logic.
// It imports the CONTRACT from generated/ (a stable type/shape), never the screen.
import { assertBookingData } from "../../generated/contracts/booking.mjs";
import { computeTotal } from "../logic/pricing.mjs";

export const bookingActions = {
  async submitBooking(data) {
    assertBookingData(data);                 // contract guard (generated)
    const total = computeTotal(data);        // business logic (dev)
    return { ok: true, id: `BK-${data.roomId}`, total };
  },
};
