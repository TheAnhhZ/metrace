// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { Batch, Dish } from "@metrace/api-client";
import { useState } from "react";
import { Badge, Button, Card } from "../../components/ui-primitives";
import { useBusinessClock } from "../../layout/business-clock";
import { BATCH_STATUS_LABELS_VI } from "../../lib/labels-vi";
import { AddBatchInputPanel } from "./add-batch-input-panel";
import { FinishBatchPanel } from "./finish-batch-panel";

type Panel = "input" | "finish" | null;

export function BatchCard(props: { batch: Batch; dishes: Dish[]; finishedBatches: Batch[]; canCook: boolean }) {
  const { batch } = props;
  const clock = useBusinessClock();
  const [panel, setPanel] = useState<Panel>(null);
  const dish = props.dishes.find((d) => d.id === batch.dish_id);
  const cooking = batch.status === "cooking";

  return (
    <Card
      title={
        <>
          <span className="font-mono">{batch.batch_code}</span> - {dish?.name ?? "Món"}
        </>
      }
      actions={<Badge tone={cooking ? "yellow" : batch.status === "finished" ? "green" : "slate"}>{BATCH_STATUS_LABELS_VI[batch.status] ?? batch.status}</Badge>}
    >
      <p className="text-lg text-slate-700">
        {batch.started_at && <>Bắt đầu {clock.time(batch.started_at)}. </>}
        {batch.finished_at && <>Xong {clock.time(batch.finished_at)}. </>}
        {batch.core_temp_c !== null && <>Nhiệt độ tâm {batch.core_temp_c} °C. </>}
        {batch.portions_produced !== null ? (
          <>
            {batch.portions_produced}/{batch.portions_planned} suất.
          </>
        ) : (
          <>Dự kiến {batch.portions_planned} suất.</>
        )}
      </p>
      {cooking && props.canCook && (
        <div className="mt-3 space-y-3">
          <div className="flex flex-wrap gap-3">
            <Button variant={panel === "input" ? "primary" : "secondary"} onClick={() => setPanel(panel === "input" ? null : "input")}>
              Thêm nguyên liệu
            </Button>
            <Button variant={panel === "finish" ? "primary" : "secondary"} onClick={() => setPanel(panel === "finish" ? null : "finish")}>
              Hoàn tất mẻ
            </Button>
          </div>
          {panel === "input" && (
            <AddBatchInputPanel
              batch={batch}
              dishes={props.dishes}
              finishedBatches={props.finishedBatches.filter((b) => b.id !== batch.id)}
              onClose={() => setPanel(null)}
            />
          )}
          {panel === "finish" && <FinishBatchPanel batch={batch} onClose={() => setPanel(null)} />}
        </div>
      )}
    </Card>
  );
}
