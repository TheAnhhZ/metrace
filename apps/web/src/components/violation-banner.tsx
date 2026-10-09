// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { ApiError, type PokaYokeFinding, describeFindingVi, messageForCode } from "@metrace/api-client";
import { Badge } from "./ui-primitives";

interface ViolationBannerProps {
  /** A failed API call; its 422 violations/warnings are shown, other errors get a generic red box. */
  error?: unknown;
  /** Explicit blocking findings (e.g. live `blockers` of a shipment). Overrides those in `error`. */
  violations?: PokaYokeFinding[];
  /** Non-blocking findings (e.g. `warnings` of a successful receiving). Overrides those in `error`. */
  warnings?: PokaYokeFinding[];
  title?: string;
}

function FindingItem({ finding, tone }: { finding: PokaYokeFinding; tone: "red" | "yellow" }) {
  const view = describeFindingVi(finding);
  return (
    <li className="space-y-1 border-t border-current/20 pt-3 first:border-t-0 first:pt-0">
      <p className="flex flex-wrap items-center gap-2 text-lg font-semibold">
        <Badge tone={tone}>{view.rule}</Badge>
        {view.subject && <span>{view.subject}:</span>}
        <span>{view.message}</span>
      </p>
      {view.measuredLimit && <p className="font-mono text-xl font-bold">{view.measuredLimit}</p>}
      {view.context.map((line) => (
        <p key={line} className="text-base">
          {line}
        </p>
      ))}
      {view.basis && <p className="text-base italic">{view.basis}</p>}
      <p className="font-mono text-sm opacity-70">{view.code}</p>
    </li>
  );
}

function GenericError({ error }: { error: unknown }) {
  const api = error instanceof ApiError ? error : undefined;
  const fields = (api?.details.errors as { loc?: unknown[] }[] | undefined)
    ?.map((e) => e.loc?.filter((p) => p !== "body").join("."))
    .filter(Boolean);
  return (
    <div role="alert" className="rounded-xl border-2 border-red-600 bg-red-50 p-4 text-red-900">
      <h3 className="text-xl font-bold">{api?.rule ? "Bị chặn - không được tiếp tục" : "Không thực hiện được"}</h3>
      <p className="mt-1 flex flex-wrap items-center gap-2 text-lg">
        {api?.rule && <Badge tone="red">{api.rule}</Badge>}
        <span>{api ? messageForCode(api.code) : messageForCode("")}</span>
      </p>
      {fields && fields.length > 0 && <p className="mt-1 text-base">Ô cần kiểm tra: {fields.join(", ")}</p>}
      {/* A business-rule validation (no field list) has no code of its own yet: show what the server said. */}
      {api?.code === "VALIDATION_ERROR" && !fields?.length && <p className="mt-1 text-base">Máy chủ báo: {api.message}</p>}
      {api?.requestId && <p className="mt-2 font-mono text-sm opacity-70">Mã yêu cầu: {api.requestId}</p>}
    </div>
  );
}

/**
 * Red = blocked by a Poka-yoke rule (what, how far off, and on what basis), yellow = warning.
 * Renders nothing when there is nothing to say.
 */
export function ViolationBanner({ error, violations, warnings, title }: ViolationBannerProps) {
  const api = error instanceof ApiError ? error : undefined;
  const blocking = violations ?? api?.violations ?? [];
  const warn = warnings ?? api?.warnings ?? [];
  const showGeneric = Boolean(error) && blocking.length === 0;

  if (!showGeneric && blocking.length === 0 && warn.length === 0) return null;
  return (
    <div className="space-y-3">
      {showGeneric && <GenericError error={error} />}
      {blocking.length > 0 && (
        <div role="alert" className="rounded-xl border-2 border-red-600 bg-red-50 p-4 text-red-900">
          <h3 className="mb-3 text-xl font-bold">{title ?? "Bị chặn - không được tiếp tục"}</h3>
          <ul className="space-y-3">
            {blocking.map((f, i) => (
              <FindingItem key={`${f.code}-${i}`} finding={f} tone="red" />
            ))}
          </ul>
        </div>
      )}
      {warn.length > 0 && (
        <div role="status" className="rounded-xl border-2 border-yellow-500 bg-yellow-50 p-4 text-yellow-900">
          <h3 className="mb-3 text-xl font-bold">Cảnh báo - vẫn được tiếp tục</h3>
          <ul className="space-y-3">
            {warn.map((f, i) => (
              <FindingItem key={`${f.code}-${i}`} finding={f} tone="yellow" />
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
