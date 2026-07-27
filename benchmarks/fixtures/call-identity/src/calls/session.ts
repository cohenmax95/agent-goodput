export type CallSession = {
  rawNumber: string;
  contactId?: string;
  brokerId?: string;
};

export function createCallSession(rawNumber: string): CallSession {
  return { rawNumber };
}

export function attachContact(session: CallSession, contactId: string): CallSession {
  return { ...session, contactId };
}

