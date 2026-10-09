// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { ACCEPTED_DOCUMENT_TYPES, type FileOut, type MealSlot, type PortalPoint } from "@metrace/api-client";
import { useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { useCreatePortalComplaint, useUploadPortalFile } from "../api/portal-api";
import { Button, Card, Field, inputClass } from "../components/ui-primitives";
import { ViolationBanner } from "../components/violation-banner";
import { useBusinessClock } from "../layout/business-clock";
import { parseDecimal } from "../lib/decimal";
import { MEAL_SLOTS, MEAL_SLOT_LABELS_VI } from "../lib/labels-vi";

const MAX_PHOTOS = 5; // the API accepts at most 5 files per complaint

/** Report a quality problem. A delivery card pre-fills date, meal and site through the URL. */
export function PortalComplaintForm({ points }: { points: PortalPoint[] }) {
  const clock = useBusinessClock();
  const [search] = useSearchParams();
  const create = useCreatePortalComplaint();
  const upload = useUploadPortalFile();
  const picker = useRef<HTMLInputElement>(null);
  const preset = points.find((p) => p.name === search.get("point"));
  const slotParam = search.get("slot") as MealSlot | null;
  const [pointId, setPointId] = useState(preset?.id ?? (points.length === 1 ? (points[0]?.id ?? "") : ""));
  const [day, setDay] = useState(search.get("date") ?? clock.day());
  const [slot, setSlot] = useState<MealSlot>(slotParam && MEAL_SLOTS.includes(slotParam) ? slotParam : "lunch");
  const [affected, setAffected] = useState("");
  const [description, setDescription] = useState("");
  const [photos, setPhotos] = useState<FileOut[]>([]);
  const [localError, setLocalError] = useState<string>();

  async function addPhotos(files: File[]) {
    for (const file of files.slice(0, MAX_PHOTOS - photos.length)) {
      try {
        const uploaded = await upload.mutateAsync(file);
        setPhotos((prev) => [...prev, uploaded]);
      } catch {
        return; // shown by the banner below
      }
    }
  }

  function submit() {
    const count = affected.trim() === "" ? 0 : parseDecimal(affected);
    if (!pointId) return setLocalError("Chọn điểm nhận hàng.");
    if (count === undefined || !Number.isInteger(count) || count < 0) return setLocalError("Số người bị ảnh hưởng phải là số nguyên không âm.");
    if (description.trim() === "") return setLocalError("Mô tả ngắn vấn đề bạn gặp (món nào, triệu chứng gì).");
    setLocalError(undefined);
    create.mutate(
      { delivery_point_id: pointId, channel: "portal", service_date: day, meal_slot: slot, affected_count: count, description, file_ids: photos.map((p) => p.id) },
      { onSuccess: () => { setAffected(""); setDescription(""); setPhotos([]); } },
    );
  }

  return (
    <Card title="Gửi phản ánh chất lượng">
      <div className="space-y-3">
        <Field label="Điểm nhận hàng">
          <select className={inputClass} value={pointId} onChange={(e) => setPointId(e.target.value)}>
            <option value="">- Chọn điểm nhận -</option>
            {points.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Ngày ăn">
            <input className={inputClass} type="date" max={clock.day()} value={day} onChange={(e) => setDay(e.target.value)} />
          </Field>
          <Field label="Bữa ăn">
            <select className={inputClass} value={slot} onChange={(e) => setSlot(e.target.value as MealSlot)}>
              {MEAL_SLOTS.map((s) => (
                <option key={s} value={s}>
                  {MEAL_SLOT_LABELS_VI[s]}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <Field label="Số người bị ảnh hưởng">
          <input className={inputClass} inputMode="numeric" placeholder="0" value={affected} onChange={(e) => setAffected(e.target.value)} />
        </Field>
        <Field label="Mô tả vấn đề">
          <textarea className={`${inputClass} min-h-28 py-2`} maxLength={2000} value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        <div className="space-y-2">
          <input
            ref={picker}
            type="file"
            multiple
            accept={ACCEPTED_DOCUMENT_TYPES.filter((t) => t.startsWith("image/")).join(",")}
            className="sr-only"
            tabIndex={-1}
            aria-hidden="true"
            onChange={(e) => {
              const files = Array.from(e.target.files ?? []);
              e.target.value = "";
              void addPhotos(files);
            }}
          />
          <Button variant="secondary" className="w-full" busy={upload.isPending} disabled={photos.length >= MAX_PHOTOS} onClick={() => picker.current?.click()}>
            Chụp hoặc chọn ảnh ({photos.length}/{MAX_PHOTOS})
          </Button>
          {photos.length > 0 && (
            <ul className="space-y-1">
              {photos.map((p) => (
                <li key={p.id} className="flex items-center justify-between gap-2 rounded-lg bg-slate-100 p-2 pl-3 text-base">
                  <span className="truncate">{p.original_name}</span>
                  <Button variant="secondary" onClick={() => setPhotos((prev) => prev.filter((x) => x.id !== p.id))}>
                    Bỏ
                  </Button>
                </li>
              ))}
            </ul>
          )}
          <ViolationBanner error={upload.error} />
        </div>
        {localError && <p role="alert" className="text-lg font-semibold text-red-800">{localError}</p>}
        {create.isSuccess && <p role="status" className="rounded-lg bg-green-50 p-3 text-lg font-semibold text-green-900">Đã gửi phản ánh {create.data.code}. Chúng tôi sẽ phản hồi trong thời hạn cam kết.</p>}
        <ViolationBanner error={create.error} />
        <Button className="w-full" busy={create.isPending} onClick={submit}>
          Gửi phản ánh
        </Button>
      </div>
    </Card>
  );
}
