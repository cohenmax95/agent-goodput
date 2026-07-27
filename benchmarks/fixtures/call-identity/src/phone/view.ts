import type { CallSession } from "../calls/session";

type Contact = {
  id: string;
  displayName: string;
  primaryPhone: string;
};

export function phoneHeader(session: CallSession, contact?: Contact) {
  return {
    title: contact?.displayName ?? session.rawNumber,
    dialedNumber: session.rawNumber,
    suggestedContactPhone: contact?.primaryPhone,
  };
}

