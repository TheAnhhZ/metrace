// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { ButtonHTMLAttributes, ReactNode } from "react";

/** Shared look for text inputs/selects: 48 px tall touch targets, large text. */
export const inputClass =
  "min-h-12 w-full rounded-lg border border-slate-400 bg-white px-3 text-lg text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-2 focus:outline-blue-700 disabled:bg-slate-100";

type ButtonVariant = "primary" | "secondary" | "danger" | "blocked";

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-blue-700 text-white hover:bg-blue-800",
  secondary: "border border-slate-400 bg-white text-slate-900 hover:bg-slate-50",
  danger: "bg-red-700 text-white hover:bg-red-800",
  // Looks unavailable but stays pressable, so the server's refusal (and why) can be shown.
  blocked: "border-2 border-dashed border-red-500 bg-red-50 text-red-800 hover:bg-red-100",
};

export function Button(props: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; busy?: boolean }) {
  const { variant = "primary", busy = false, className = "", disabled, children, ...rest } = props;
  return (
    <button
      type="button"
      {...rest}
      disabled={disabled || busy}
      className={`min-h-12 min-w-12 rounded-lg px-5 text-lg font-semibold disabled:cursor-not-allowed disabled:opacity-50 ${BUTTON_VARIANTS[variant]} ${className}`}
    >
      {busy ? "Đang xử lý..." : children}
    </button>
  );
}

type BadgeTone = "green" | "yellow" | "red" | "slate" | "blue";

const BADGE_TONES: Record<BadgeTone, string> = {
  green: "bg-green-100 text-green-900 ring-green-600",
  yellow: "bg-yellow-100 text-yellow-900 ring-yellow-600",
  red: "bg-red-100 text-red-900 ring-red-600",
  slate: "bg-slate-100 text-slate-800 ring-slate-400",
  blue: "bg-blue-100 text-blue-900 ring-blue-600",
};

export function Badge({ tone = "slate", children }: { tone?: BadgeTone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-full px-3 py-1 text-base font-semibold ring-1 ring-inset ${BADGE_TONES[tone]}`}>
      {children}
    </span>
  );
}

export function Card({ title, actions, children }: { title?: ReactNode; actions?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
      {(title || actions) && (
        <header className="mb-3 flex flex-wrap items-center justify-between gap-2">
          {title && <h2 className="text-xl font-bold">{title}</h2>}
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-base font-semibold text-slate-700">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-sm text-slate-600">{hint}</span>}
    </label>
  );
}

export function PageTitle({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="mb-4">
      <h1 className="text-3xl font-bold">{children}</h1>
      {hint && <p className="mt-1 text-lg text-slate-600">{hint}</p>}
    </div>
  );
}

/** Shown instead of an action the signed-in role may not perform. */
export function RoleNotice({ children }: { children: ReactNode }) {
  return <p className="rounded-lg bg-slate-100 p-3 text-base text-slate-700">{children}</p>;
}
