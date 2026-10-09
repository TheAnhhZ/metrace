// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import type { Lineage } from "@metrace/api-client";
import cytoscape from "cytoscape";
import { useEffect, useMemo, useRef } from "react";
import { Button } from "../../components/ui-primitives";
import { buildElements } from "./lineage-elements";

/** Fit-to-view shrinks big graphs until the labels are unreadable; below this zoom we stay readable and let the user pan. */
const MIN_READABLE_ZOOM = 0.85;

const STYLE: cytoscape.StylesheetJson = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "text-wrap": "wrap",
      "text-max-width": "130px",
      "font-size": 15,
      "text-valign": "center",
      "text-halign": "center",
      color: "#0f172a",
      "background-color": "#e2e8f0",
      "border-width": 2,
      "border-color": "#64748b",
      shape: "round-rectangle",
      width: "label",
      height: "label",
      padding: "10px",
    },
  },
  { selector: "node.supplier", style: { shape: "hexagon", "border-color": "#7c3aed" } },
  { selector: "node.lot", style: { "border-color": "#0369a1" } },
  { selector: "node.batch", style: { shape: "rectangle", "border-color": "#15803d" } },
  { selector: "node.shipment", style: { shape: "cut-rectangle", "border-color": "#a16207" } },
  { selector: "node.delivery_point", style: { shape: "ellipse", "border-color": "#334155" } },
  { selector: "node.asset", style: { shape: "tag", "border-color": "#0e7490" } },
  { selector: "node.locked", style: { "background-color": "#dc2626", color: "#ffffff", "border-color": "#7f1d1d" } },
  { selector: "node.held", style: { "background-color": "#fbbf24", "border-color": "#b45309" } },
  { selector: "node.recall", style: { "background-color": "#fb923c", "border-color": "#9a3412", "border-style": "dashed", "border-width": 3 } },
  { selector: "node.root", style: { "border-width": 5 } },
  { selector: "node:selected", style: { "overlay-color": "#1d4ed8", "overlay-opacity": 0.25, "overlay-padding": 8 } },
  {
    selector: "edge",
    style: { width: 2, "line-color": "#94a3b8", "target-arrow-color": "#94a3b8", "target-arrow-shape": "triangle", "curve-style": "bezier" },
  },
];

/**
 * Graph view of a lineage (Cytoscape, built-in breadthfirst layout only). Edges are drawn in the
 * direction goods flow; the layout fans out from the root in both directions. Clicking a node
 * reports its "type:id" key. `onError` lets the page fall back to the table.
 */
export function LineageGraph(props: { lineage: Lineage; selected?: string; onSelect: (key: string) => void; onError: () => void }) {
  const container = useRef<HTMLDivElement>(null);
  const cy = useRef<cytoscape.Core | undefined>(undefined);
  const elements = useMemo(() => buildElements(props.lineage), [props.lineage]);
  const { onSelect, onError } = props;

  useEffect(() => {
    if (!container.current) return;
    try {
      const instance = cytoscape({
        container: container.current,
        elements,
        style: STYLE,
        layout: { name: "breadthfirst", roots: [props.lineage.root], directed: false, spacingFactor: 1.15, padding: 24 },
        wheelSensitivity: 0.25,
        minZoom: 0.2,
        maxZoom: 2.5,
      });
      if (instance.zoom() < MIN_READABLE_ZOOM) {
        // Everything fans out below the root, so pin the root to the top-centre of the canvas.
        const rootPosition = instance.getElementById(props.lineage.root).position();
        instance.zoom(MIN_READABLE_ZOOM);
        instance.pan({ x: instance.width() / 2 - rootPosition.x * MIN_READABLE_ZOOM, y: 60 - rootPosition.y * MIN_READABLE_ZOOM });
      }
      instance.on("tap", "node", (event) => onSelect(event.target.id() as string));
      cy.current = instance;
      return () => {
        instance.destroy();
        cy.current = undefined;
      };
    } catch (error) {
      console.error("lineage graph failed", error);
      onError();
    }
  }, [elements, props.lineage.root, onSelect, onError]);

  useEffect(() => {
    const instance = cy.current;
    if (!instance) return;
    instance.nodes().unselect();
    if (props.selected) instance.getElementById(props.selected).select();
  }, [props.selected, elements]);

  const zoomBy = (factor: number) => {
    const instance = cy.current;
    if (instance) instance.zoom({ level: instance.zoom() * factor, renderedPosition: { x: instance.width() / 2, y: instance.height() / 2 } });
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="secondary" aria-label="Phóng to" onClick={() => zoomBy(1.25)}>
          +
        </Button>
        <Button variant="secondary" aria-label="Thu nhỏ" onClick={() => zoomBy(0.8)}>
          -
        </Button>
        <Button variant="secondary" onClick={() => cy.current?.fit(undefined, 24)}>
          Vừa khung
        </Button>
        <span className="text-base text-slate-600">Kéo để di chuyển, chạm một nút để xem chi tiết.</span>
      </div>
      <div
        ref={container}
        role="img"
        aria-label={`Đồ thị truy vết ${props.lineage.nodes.length} nút. Dùng chế độ Bảng để đọc chi tiết.`}
        className="h-[28rem] w-full rounded-xl bg-white ring-1 ring-slate-300 md:h-[34rem]"
      />
    </div>
  );
}
