// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { Sample } from "@metrace/api-client";
import { useState } from "react";
import { useDiscardSample } from "../../api/mutations";
import { useSealImageUrl } from "../../api/use-seal-image-url";
import { CountdownTimer } from "../../components/countdown-timer";
import { Badge, Button } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { useBusinessClock } from "../../layout/business-clock";
import { remainingMs } from "../../lib/server-clock";

function SealImage({ sample }: { sample: Sample }) {
  const { url, error } = useSealImageUrl(sample.id);
  const box = "flex size-40 shrink-0 items-center justify-center rounded-lg bg-white p-1 ring-1 ring-slate-300";
  if (url) {
    return (
      <div className={box}>
        <img src={url} alt={`Mã QR niêm phong ${sample.seal_code}`} className="size-full" />
      </div>
    );
  }
  return <div className={`${box} text-center text-base text-slate-500`}>{error ? "Không tải được mã QR" : "Đang tải mã QR..."}</div>;
}

/** One retained sample: QR seal, quantity, server-time countdown, and (QA only) discard. */
export function SampleCard(props: { sample: Sample; batchLabel: string; offsetMs: number; canDiscard: boolean }) {
  const { sample, offsetMs } = props;
  const clock = useBusinessClock();
  const discard = useDiscardSample();
  const [confirming, setConfirming] = useState(false);
  const stored = sample.status === "stored";
  const eligible = remainingMs(sample.eligible_discard_at, Date.now(), offsetMs) <= 0;

  return (
    <article className={`rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200 ${stored ? "" : "opacity-60"}`}>
      <div className="flex gap-4">
        <SealImage sample={sample} />
        <div className="min-w-0 flex-1 space-y-1">
          <p className="font-mono text-xl font-bold">{sample.seal_code}</p>
          <p className="text-lg">{props.batchLabel}</p>
          <p className="text-lg">
            {sample.qty_g !== null ? `${sample.qty_g} g` : `${sample.qty_ml ?? "?"} ml`} - lưu lúc {clock.dateTime(sample.stored_at)}
          </p>
          {stored ? (
            <div>
              <p className="text-base text-slate-600">Được hủy sau (giờ máy chủ):</p>
              <CountdownTimer target={sample.eligible_discard_at} offsetMs={offsetMs} doneLabel="Đủ điều kiện hủy" />
              <p className="text-base text-slate-600">Hạn hủy sớm nhất: {clock.dateTime(sample.eligible_discard_at)}</p>
            </div>
          ) : (
            <Badge>Đã hủy {sample.discarded_at ? clock.dateTime(sample.discarded_at) : ""}</Badge>
          )}
        </div>
      </div>
      {stored && props.canDiscard && (
        <div className="mt-3 space-y-3">
          {confirming ? (
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-lg font-semibold">Hủy mẫu {sample.seal_code}?</span>
              <Button variant="danger" busy={discard.isPending} onClick={() => discard.mutate(sample.id, { onSettled: () => setConfirming(false) })}>
                Xác nhận hủy
              </Button>
              <Button variant="secondary" onClick={() => setConfirming(false)}>
                Không
              </Button>
            </div>
          ) : (
            <Button variant={eligible ? "danger" : "blocked"} onClick={() => setConfirming(true)}>
              Hủy mẫu
            </Button>
          )}
          {!eligible && !confirming && <p className="text-base text-red-800">Chưa đủ thời gian lưu mẫu - hệ thống sẽ từ chối nếu hủy lúc này.</p>}
          <ViolationBanner error={discard.error} />
        </div>
      )}
    </article>
  );
}
