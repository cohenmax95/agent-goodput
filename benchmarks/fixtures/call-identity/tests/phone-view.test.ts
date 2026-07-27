import { strict as assert } from "node:assert";
import { attachContact, createCallSession } from "../src/calls/session";
import { phoneHeader } from "../src/phone/view";

const session = attachContact(createCallSession("+12395550100"), "contact-7");
const header = phoneHeader(session, {
  id: "contact-7",
  displayName: "Seller",
  primaryPhone: "+18135550199",
});

assert.equal(header.dialedNumber, "+12395550100");

