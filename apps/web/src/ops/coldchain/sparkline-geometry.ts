// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { parseInstant } from "../../lib/server-clock";

export interface SparkReading {
  at: string;
  temp_c: number | string;
}

export interface SparkLimits {
  min_c?: number | string | null;
  max_c?: number | string | null;
}

export interface Sparkline {
  /** SVG polyline `points` attribute. */
  points: string;
  dots: { x: number; y: number; temp: number; breach: boolean }[];
  /** y of the max/min threshold lines when set. */
  maxY?: number;
  minY?: number;
  yMin: number;
  yMax: number;
  last: { x: number; y: number; temp: number };
}

const num = (v: number | string | null | undefined): number | undefined => {
  if (v === null || v === undefined || v === "") return undefined;
  const n = Number(v);
  return Number.isFinite(n) ? n : undefined;
};

/**
 * Turn readings into SVG coordinates (x by time, y by temperature, both padded). The y range always
 * includes the limits so a breach is visible as the line crossing the red threshold.
 */
export function buildSparkline(
  readings: SparkReading[],
  limits: SparkLimits,
  size: { width: number; height: number; pad: number },
): Sparkline | undefined {
  const pts = readings
    .map((r) => ({ t: parseInstant(r.at), temp: num(r.temp_c) }))
    .filter((p): p is { t: number; temp: number } => !Number.isNaN(p.t) && p.temp !== undefined)
    .sort((a, b) => a.t - b.t);
  if (pts.length === 0) return undefined;

  const maxC = num(limits.max_c);
  const minC = num(limits.min_c);
  const values = [...pts.map((p) => p.temp), ...(maxC !== undefined ? [maxC] : []), ...(minC !== undefined ? [minC] : [])];
  const yMin = Math.min(...values) - 1;
  const yMax = Math.max(...values) + 1;
  const t0 = pts[0]?.t ?? 0;
  const t1 = pts[pts.length - 1]?.t ?? t0;
  const spanT = t1 - t0 || 1;
  const innerW = size.width - 2 * size.pad;
  const innerH = size.height - 2 * size.pad;
  const x = (t: number) => size.pad + (pts.length === 1 ? innerW : ((t - t0) / spanT) * innerW);
  const y = (v: number) => size.pad + (1 - (v - yMin) / (yMax - yMin)) * innerH;

  const dots = pts.map((p) => ({ x: x(p.t), y: y(p.temp), temp: p.temp, breach: maxC !== undefined && p.temp > maxC }));
  const lastDot = dots[dots.length - 1] as Sparkline["dots"][number];
  return {
    points: dots.map((d) => `${d.x.toFixed(1)},${d.y.toFixed(1)}`).join(" "),
    dots,
    maxY: maxC !== undefined ? y(maxC) : undefined,
    minY: minC !== undefined ? y(minC) : undefined,
    yMin,
    yMax,
    last: lastDot,
  };
}
