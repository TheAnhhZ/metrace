// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { useAssetReadings } from "../../api/coldchain-audit-api";
import { QueryBoundary } from "../../components/query-boundary";
import { plainNumber } from "@metrace/api-client";
import { buildSparkline } from "./sparkline-geometry";

const SIZE = { width: 480, height: 140, pad: 14 } as const;

/** Hand-drawn SVG chart of the last hour of fridge readings with the allowed range as dashed lines. */
export function TemperatureSparkline({ assetCode, minutes = 60 }: { assetCode: string; minutes?: number }) {
  const readings = useAssetReadings(assetCode, minutes);
  return (
    <QueryBoundary query={readings}>
      {(data) => {
        const spark = buildSparkline(data.readings, data, SIZE);
        if (!spark) return <p className="text-lg text-slate-600">Chưa có số đo trong {minutes} phút qua.</p>;
        return (
          <figure>
            <svg
              viewBox={`0 0 ${SIZE.width} ${SIZE.height}`}
              role="img"
              aria-label={`Nhiệt độ ${assetCode} trong ${minutes} phút qua, hiện tại ${plainNumber(spark.last.temp)} độ C`}
              className="h-auto w-full max-w-xl rounded-lg bg-white"
            >
              {spark.maxY !== undefined && (
                <g>
                  <line x1={SIZE.pad} x2={SIZE.width - SIZE.pad} y1={spark.maxY} y2={spark.maxY} stroke="#dc2626" strokeDasharray="6 4" />
                  <text x={SIZE.width - SIZE.pad} y={spark.maxY - 4} textAnchor="end" fontSize="12" fill="#b91c1c">
                    tối đa {plainNumber(data.max_c ?? "")} °C
                  </text>
                </g>
              )}
              {spark.minY !== undefined && (
                <g>
                  <line x1={SIZE.pad} x2={SIZE.width - SIZE.pad} y1={spark.minY} y2={spark.minY} stroke="#2563eb" strokeDasharray="6 4" />
                  <text x={SIZE.width - SIZE.pad} y={spark.minY - 4} textAnchor="end" fontSize="12" fill="#1d4ed8">
                    tối thiểu {plainNumber(data.min_c ?? "")} °C
                  </text>
                </g>
              )}
              <polyline points={spark.points} fill="none" stroke="#0f172a" strokeWidth="2" strokeLinejoin="round" />
              {spark.dots.map((d) => (
                <circle key={`${d.x}-${d.y}`} cx={d.x} cy={d.y} r={d.breach ? 3.5 : 2} fill={d.breach ? "#dc2626" : "#0f172a"} />
              ))}
            </svg>
            <figcaption className="mt-1 text-base text-slate-700">
              {spark.dots.length} số đo trong {minutes} phút qua. Số đo gần nhất: <strong>{plainNumber(spark.last.temp)} °C</strong>.
            </figcaption>
          </figure>
        );
      }}
    </QueryBoundary>
  );
}
