// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { DeliveryPoint, MealSlot } from "@metrace/api-client";
import { useState } from "react";
import { useCreateComplaint } from "../../api/incident-mutations";
import { Button, Card, Field, inputClass } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { useBusinessClock } from "../../layout/business-clock";
import { parseDecimal } from "../../lib/decimal";
import { MEAL_SLOTS, MEAL_SLOT_LABELS_VI } from "../../lib/labels-vi";

/** Intake of a complaint received by phone or at the CSKH desk (customers use the portal instead). */
export function ComplaintIntakeForm({ points }: { points: DeliveryPoint[] }) {
  const clock = useBusinessClock();
  const create = useCreateComplaint();
  const [pointId, setPointId] = useState("");
  const [channel, setChannel] = useState<"phone" | "cskh">("phone");
  const [day, setDay] = useState(clock.day());
  const [slot, setSlot] = useState<MealSlot>("lunch");
  const [affected, setAffected] = useState("");
  const [description, setDescription] = useState("");
  const [localError, setLocalError] = useState<string>();

  function submit() {
    const count = affected.trim() === "" ? 0 : parseDecimal(affected);
    if (!pointId) return setLocalError("Chọn điểm giao bị ảnh hưởng.");
    if (count === undefined || !Number.isInteger(count) || count < 0) return setLocalError("Số người bị ảnh hưởng phải là số nguyên không âm.");
    setLocalError(undefined);
    create.mutate(
      { delivery_point_id: pointId, channel, service_date: day, meal_slot: slot, affected_count: count, description },
      { onSuccess: () => { setPointId(""); setAffected(""); setDescription(""); } },
    );
  }

  return (
    <Card title="Ghi nhận phản ánh mới">
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        <div className="md:col-span-2">
          <Field label="Điểm giao">
            <select className={inputClass} value={pointId} onChange={(e) => setPointId(e.target.value)}>
              <option value="">- Chọn điểm giao -</option>
              {points.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} - {p.customer_name}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <Field label="Kênh nhận">
          <select className={inputClass} value={channel} onChange={(e) => setChannel(e.target.value as "phone" | "cskh")}>
            <option value="phone">Điện thoại</option>
            <option value="cskh">CSKH trực tiếp</option>
          </select>
        </Field>
        <Field label="Số người bị ảnh hưởng">
          <input className={inputClass} inputMode="numeric" value={affected} onChange={(e) => setAffected(e.target.value)} placeholder="0" />
        </Field>
        <Field label="Ngày phục vụ">
          <input className={inputClass} type="date" value={day} onChange={(e) => setDay(e.target.value)} />
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
        <div className="md:col-span-2">
          <Field label="Mô tả (triệu chứng, món nghi ngờ)">
            <input className={inputClass} value={description} onChange={(e) => setDescription(e.target.value)} maxLength={2000} />
          </Field>
        </div>
      </div>
      {localError && <p role="alert" className="mt-3 text-lg font-semibold text-red-800">{localError}</p>}
      <div className="mt-3 space-y-3">
        <Button busy={create.isPending} onClick={submit}>
          Ghi nhận phản ánh
        </Button>
        <ViolationBanner error={create.error} />
      </div>
    </Card>
  );
}
