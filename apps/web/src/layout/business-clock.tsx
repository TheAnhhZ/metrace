// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { WhoAmI } from "@metrace/api-client";
import { type ReactNode, createContext, useContext, useMemo } from "react";
import { businessDay, formatDateTime, formatTime } from "../lib/server-clock";

export interface BusinessClock {
  whoami: WhoAmI;
  /** Server minus tablet clock (ms) when whoami was fetched. */
  offsetMs: number;
  tz: string;
  /** Today's business date (YYYY-MM-DD) on the server's clock and time zone. */
  day: () => string;
  time: (iso: string) => string;
  dateTime: (iso: string) => string;
}

const Ctx = createContext<BusinessClock | null>(null);

export function BusinessClockProvider(props: { whoami: WhoAmI; offsetMs: number; children: ReactNode }) {
  const { whoami, offsetMs } = props;
  const value = useMemo<BusinessClock>(() => {
    const tz = whoami.business_tz;
    return {
      whoami,
      offsetMs,
      tz,
      day: () => businessDay(Date.now() + offsetMs, tz),
      time: (iso) => formatTime(iso, tz),
      dateTime: (iso) => formatDateTime(iso, tz),
    };
  }, [whoami, offsetMs]);
  return <Ctx.Provider value={value}>{props.children}</Ctx.Provider>;
}

/** Server-based "today" and time formatting; only valid below the app shell (which loads whoami). */
export function useBusinessClock(): BusinessClock {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useBusinessClock must be used inside BusinessClockProvider");
  return ctx;
}
