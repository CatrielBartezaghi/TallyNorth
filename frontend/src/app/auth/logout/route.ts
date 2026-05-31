import { NextRequest } from "next/server";

import { redirectWithClearedSession } from "../_session";

export async function POST(request: NextRequest) {
  return redirectWithClearedSession(request);
}
