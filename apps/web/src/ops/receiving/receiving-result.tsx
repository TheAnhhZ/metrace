// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { type Ingredient, type ReceivingOut, toFindings } from "@metrace/api-client";
import { Button, Card } from "../../components/ui-primitives";
import { ViolationBanner } from "../../components/violation-banner";
import { useBusinessClock } from "../../layout/business-clock";

/** Confirmation after a successful receiving: new lots, plus any warnings (yellow). */
export function ReceivingResult(props: { result: ReceivingOut; ingredients: Ingredient[]; onClose: () => void }) {
  const { result, ingredients } = props;
  const clock = useBusinessClock();
  return (
    <div className="mb-4 space-y-3">
      <div role="status" className="rounded-xl border-2 border-green-600 bg-green-50 p-4 text-green-900">
        <h2 className="text-xl font-bold">
          Đã nhận hàng {result.code} lúc {clock.time(result.received_at)}
        </h2>
        <ul className="mt-2 space-y-1 text-lg">
          {result.lots.map((lot) => (
            <li key={lot.id}>
              Lô <span className="font-mono font-bold">{lot.lot_code}</span> -{" "}
              {ingredients.find((i) => i.id === lot.ingredient_id)?.name ?? "Nguyên liệu"}: {lot.qty_kg} kg
              {lot.temp_c !== null && `, ${lot.temp_c} °C`}
            </li>
          ))}
        </ul>
      </div>
      <ViolationBanner warnings={toFindings(result.warnings)} />
      <Card>
        <Button variant="secondary" onClick={props.onClose}>
          Nhận lô hàng khác
        </Button>
      </Card>
    </div>
  );
}
