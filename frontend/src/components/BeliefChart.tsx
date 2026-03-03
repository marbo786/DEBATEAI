/**
 * BeliefChart — animated SVG belief trajectory chart.
 *
 * Design goals:
 *  - Clear zones: "PRO winning" (top half) vs "CON winning" (bottom half)
 *  - Human-readable hover tooltips: "R2 PRO · 63%"
 *  - Turning point shown as a highlighted column for the whole round
 *  - Round winner chips below X-axis labels (P / C / =)
 *  - Start + Final annotations
 */
import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface BeliefChartProps {
    beliefHistory: number[];   // 0.0–1.0; index 0 = prior, index n = after move n
    maxRounds: number;
    turningPointRound?: number | null;
    className?: string;
}

const W = 600;
const H = 200;
const PAD = { top: 28, right: 24, bottom: 42, left: 48 };

function toX(i: number, total: number): number {
    const iw = W - PAD.left - PAD.right;
    return PAD.left + (total <= 1 ? iw / 2 : (i / (total - 1)) * iw);
}
function toY(belief: number): number {
    return PAD.top + (1 - belief) * (H - PAD.top - PAD.bottom);
}
function makePath(pts: [number, number][]): string {
    if (pts.length < 2) return "";
    let d = `M ${pts[0][0]} ${pts[0][1]}`;
    for (let i = 1; i < pts.length; i++) {
        const [x1, y1] = pts[i - 1], [x2, y2] = pts[i];
        const cx = (x1 + x2) / 2;
        d += ` C ${cx} ${y1} ${cx} ${y2} ${x2} ${y2}`;
    }
    return d;
}
function makeArea(pts: [number, number][]): string {
    if (pts.length < 2) return "";
    const mid = toY(0.5);
    let d = `M ${pts[0][0]} ${mid} L ${pts[0][0]} ${pts[0][1]}`;
    for (let i = 1; i < pts.length; i++) {
        const [x1, y1] = pts[i - 1], [x2, y2] = pts[i];
        const cx = (x1 + x2) / 2;
        d += ` C ${cx} ${y1} ${cx} ${y2} ${x2} ${y2}`;
    }
    d += ` L ${pts[pts.length - 1][0]} ${mid} Z`;
    return d;
}

/** Human-readable label for a belief_history index */
function moveLabel(idx: number): string {
    if (idx === 0) return "Start";
    return `R${Math.ceil(idx / 2)} ${idx % 2 === 1 ? "PRO" : "CON"}`;
}

export default function BeliefChart({
    beliefHistory,
    maxRounds,
    turningPointRound,
    className = "",
}: BeliefChartProps) {
    const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

    const pts = useMemo<[number, number][]>(() => {
        if (!beliefHistory || beliefHistory.length < 2) return [];
        return beliefHistory.map((b, i) => [toX(i, beliefHistory.length), toY(b)]);
    }, [beliefHistory]);

    const linePath = useMemo(() => makePath(pts), [pts]);
    const areaPath = useMemo(() => makeArea(pts), [pts]);

    // Per-complete-round data: winner, net shift, x-bounds for column
    const roundData = useMemo(() => {
        const n = beliefHistory.length;
        const rounds: Array<{
            k: number;
            label: string;
            winner: "pro" | "con" | "tie";
            x: number;           // X of the CON move (end of round)
            colX1: number;       // left column boundary
            colX2: number;       // right column boundary
        }> = [];
        for (let k = 1; k * 2 < n; k++) {
            const before = beliefHistory[k * 2 - 2];
            const after = beliefHistory[k * 2];
            const winner = after > before + 0.005 ? "pro" : after < before - 0.005 ? "con" : "tie";
            // Column spans from the PRO move to the CON move of this round
            const xPro = toX(k * 2 - 1, n);
            const xCon = toX(k * 2, n);
            const halfStep = (toX(1, n) - toX(0, n)) / 2;
            rounds.push({
                k,
                label: `R${k}`,
                winner,
                x: xCon,
                colX1: xPro - halfStep * 0.8,
                colX2: xCon + halfStep * 0.8,
            });
        }
        return rounds;
    }, [beliefHistory]);

    const midY = toY(0.5);
    const innerH = H - PAD.top - PAD.bottom;
    const lastBelief = beliefHistory[beliefHistory.length - 1] ?? 0.5;
    const isProLeading = lastBelief > 0.5;
    const n = beliefHistory.length;

    if (pts.length < 2) return null;

    return (
        <div className={`relative ${className}`}>
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
                <div>
                    <p className="text-[10px] font-bold tracking-widest text-slate-500 uppercase">
                        Audience Belief Trajectory
                    </p>
                    <p className="text-[10px] text-slate-600 mt-0.5">
                        How persuaded the audience was — round by round
                    </p>
                </div>
                {turningPointRound && (
                    <div className="text-right">
                        <p className="text-[10px] text-amber-500/80 font-semibold">⚡ Turning Point</p>
                        <p className="text-[10px] text-amber-400 font-bold">Round {turningPointRound}</p>
                    </div>
                )}
            </div>

            <div className="relative rounded-xl border border-white/[0.06] bg-slate-900/60 overflow-hidden">
                <svg
                    viewBox={`0 0 ${W} ${H}`}
                    className="w-full h-[130px] sm:h-[160px]"
                    onMouseLeave={() => setHoveredIdx(null)}
                >
                    <defs>
                        <linearGradient id="proGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#10b981" stopOpacity="0.25" />
                            <stop offset="100%" stopColor="#10b981" stopOpacity="0.02" />
                        </linearGradient>
                        <linearGradient id="conGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.02" />
                            <stop offset="100%" stopColor="#f43f5e" stopOpacity="0.25" />
                        </linearGradient>
                        <clipPath id="aboveMid">
                            <rect x="0" y="0" width={W} height={midY} />
                        </clipPath>
                        <clipPath id="belowMid">
                            <rect x="0" y={midY} width={W} height={H - midY} />
                        </clipPath>
                        <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
                            <stop offset="0%" stopColor={isProLeading ? "#34d399" : "#fb7185"} stopOpacity="0.5" />
                            <stop offset="100%" stopColor={isProLeading ? "#10b981" : "#f43f5e"} />
                        </linearGradient>
                    </defs>

                    {/* Zone labels */}
                    <text x={PAD.left + 6} y={PAD.top + 14} fontSize="9" fill="#10b981" opacity={0.5} fontWeight="bold">
                        PRO WINNING
                    </text>
                    <text x={PAD.left + 6} y={H - PAD.bottom - 6} fontSize="9" fill="#f43f5e" opacity={0.5} fontWeight="bold">
                        CON WINNING
                    </text>

                    {/* Grid lines */}
                    {[0, 0.25, 0.5, 0.75, 1].map((v) => {
                        const y = toY(v);
                        const isMid = v === 0.5;
                        return (
                            <line
                                key={v}
                                x1={PAD.left} y1={y} x2={W - PAD.right} y2={y}
                                stroke={isMid ? "#1e40af" : "#1e293b"}
                                strokeWidth={isMid ? 1.5 : 0.8}
                                strokeDasharray={isMid ? "6 3" : "3 6"}
                                opacity={isMid ? 0.8 : 0.5}
                            />
                        );
                    })}

                    {/* Turning point column highlight */}
                    {turningPointRound && roundData.find(r => r.k === turningPointRound) && (() => {
                        const rd = roundData.find(r => r.k === turningPointRound)!;
                        return (
                            <rect
                                x={rd.colX1}
                                y={PAD.top}
                                width={rd.colX2 - rd.colX1}
                                height={innerH}
                                fill="#f59e0b"
                                opacity={0.07}
                                rx={3}
                            />
                        );
                    })()}

                    {/* Area fills */}
                    <motion.path d={areaPath} fill="url(#proGrad)" clipPath="url(#aboveMid)"
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5, delay: 0.2 }} />
                    <motion.path d={areaPath} fill="url(#conGrad)" clipPath="url(#belowMid)"
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5, delay: 0.2 }} />

                    {/* Animated line */}
                    <motion.path
                        key={n}
                        d={linePath}
                        fill="none"
                        stroke="url(#lineGrad)"
                        strokeWidth={2.5}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        initial={{ pathLength: 0, opacity: 0 }}
                        animate={{ pathLength: 1, opacity: 1 }}
                        transition={{ duration: 0.9, ease: "easeOut" }}
                    />

                    {/* Y-axis labels */}
                    {[
                        { v: 1, label: "100%", color: "#10b981" },
                        { v: 0.75, label: "75%", color: "#475569" },
                        { v: 0.5, label: "50%", color: "#3b82f6" },
                        { v: 0.25, label: "25%", color: "#475569" },
                        { v: 0, label: "0%", color: "#f43f5e" },
                    ].map(({ v, label, color }) => (
                        <text key={v} x={PAD.left - 4} y={toY(v) + 4}
                            textAnchor="end" fontSize="9" fill={color} opacity={0.8}>
                            {label}
                        </text>
                    ))}

                    {/* X-axis round labels + winner chips */}
                    {roundData.map(({ k, label, winner, x }) => {
                        const isTP = k === turningPointRound;
                        const chipColor = winner === "pro" ? "#10b981" : winner === "con" ? "#f43f5e" : "#64748b";
                        const chipText = winner === "pro" ? "P" : winner === "con" ? "C" : "=";
                        return (
                            <g key={k}>
                                {/* Round label */}
                                <text
                                    x={x} y={H - PAD.bottom + 13}
                                    textAnchor="middle" fontSize="9"
                                    fill={isTP ? "#f59e0b" : "#475569"}
                                    fontWeight={isTP ? "bold" : "normal"}
                                >
                                    {label}
                                </text>
                                {/* Winner chip */}
                                <circle cx={x} cy={H - PAD.bottom + 25} r={5.5} fill={chipColor} opacity={0.25} />
                                <text x={x} y={H - PAD.bottom + 29}
                                    textAnchor="middle" fontSize="8" fontWeight="bold"
                                    fill={chipColor}
                                >
                                    {chipText}
                                </text>
                            </g>
                        );
                    })}

                    {/* "Tied →" label on the 50% line */}
                    <text x={W - PAD.right + 2} y={midY + 4}
                        fontSize="8" fill="#3b82f6" opacity={0.7}>
                        Tied
                    </text>

                    {/* Hover dots */}
                    {pts.map(([x, y], i) => {
                        const isHov = hoveredIdx === i;
                        const b = beliefHistory[i];
                        const isTP = turningPointRound !== null && turningPointRound !== undefined &&
                            i >= turningPointRound * 2 - 1 && i <= turningPointRound * 2;
                        return (
                            <g key={i}>
                                <rect x={x - 10} y={PAD.top} width={20} height={innerH}
                                    fill="transparent" onMouseEnter={() => setHoveredIdx(i)} />
                                <motion.circle cx={x} cy={y}
                                    r={isHov ? 5.5 : isTP ? 4 : 3}
                                    fill={isTP && !isHov ? "#f59e0b" : b > 0.5 ? "#10b981" : b < 0.5 ? "#f43f5e" : "#64748b"}
                                    stroke={isHov ? "white" : "transparent"}
                                    strokeWidth={1.5}
                                    animate={{ r: isHov ? 5.5 : isTP ? 4 : 3 }}
                                    transition={{ duration: 0.12 }}
                                />
                            </g>
                        );
                    })}

                    {/* Start annotation */}
                    {pts[0] && (() => {
                        const [x, y] = pts[0];
                        const b = beliefHistory[0];
                        return (
                            <g>
                                <circle cx={x} cy={y} r={4} fill="#64748b" />
                                <text x={x + 6} y={y - 6} fontSize="9" fill="#64748b">
                                    Start {Math.round(b * 100)}%
                                </text>
                            </g>
                        );
                    })()}

                    {/* Final annotation */}
                    {pts.length > 1 && (() => {
                        const [x, y] = pts[pts.length - 1];
                        const b = lastBelief;
                        const pct = Math.round(b * 100);
                        const color = b > 0.5 ? "#10b981" : b < 0.5 ? "#f43f5e" : "#64748b";
                        const label = b > 0.5 ? `PRO ${pct}%` : b < 0.5 ? `CON ${100 - pct}%` : "Tied 50%";
                        const tx = x > W - 80 ? x - 4 : x + 6;
                        const anchor = x > W - 80 ? "end" : "start";
                        return (
                            <g>
                                <circle cx={x} cy={y} r={5} fill={color} opacity={0.9} />
                                <text x={tx} y={y - 7} fontSize="9.5" fill={color} fontWeight="bold" textAnchor={anchor}>
                                    {label}
                                </text>
                            </g>
                        );
                    })()}

                    {/* Hover tooltip */}
                    <AnimatePresence>
                        {hoveredIdx !== null && pts[hoveredIdx] && (() => {
                            const [x, y] = pts[hoveredIdx];
                            const b = beliefHistory[hoveredIdx];
                            const label = moveLabel(hoveredIdx);
                            const pct = Math.round(b * 100);
                            const color = b > 0.5 ? "#34d399" : b < 0.5 ? "#fb7185" : "#94a3b8";
                            const side = hoveredIdx === 0 ? null : hoveredIdx % 2 === 1 ? "pro" : "con";
                            const sideLabel = side === "pro" ? "PRO argued" : side === "con" ? "CON argued" : null;
                            const tx = x > W - 100 ? x - 6 : x + 8;
                            const anchor = x > W - 100 ? "end" : "start";
                            return (
                                <motion.g key={hoveredIdx}
                                    initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }} transition={{ duration: 0.1 }}>
                                    <rect
                                        x={tx - (anchor === "end" ? 88 : 0)} y={y - 36}
                                        width={90} height={34} rx={5}
                                        fill="#0f172a" stroke="#334155" strokeWidth={0.8}
                                    />
                                    <text x={tx - (anchor === "end" ? 82 : -6)} y={y - 22}
                                        fontSize="9" fill="#94a3b8">{label}</text>
                                    {sideLabel && (
                                        <text x={tx - (anchor === "end" ? 82 : -6)} y={y - 12}
                                            fontSize="8" fill="#475569">{sideLabel}</text>
                                    )}
                                    <text x={tx + (anchor === "end" ? -6 : 84)} y={y - 22}
                                        fontSize="10" fontWeight="bold" fill={color} textAnchor="end">
                                        {pct}%
                                    </text>
                                </motion.g>
                            );
                        })()}
                    </AnimatePresence>
                </svg>

                {/* Legend strip */}
                <div className="flex items-center justify-between px-3 py-1.5 border-t border-white/[0.04] bg-slate-950/30">
                    <div className="flex items-center gap-3 text-[9px] text-slate-500">
                        <span className="flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-emerald-500/80" /> PRO gaining
                        </span>
                        <span className="flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-rose-500/80" /> CON gaining
                        </span>
                        <span className="flex items-center gap-1">
                            <span className="w-3 h-0.5 bg-blue-400/60 rounded" /> 50% neutral
                        </span>
                    </div>
                    <div className="flex items-center gap-2 text-[9px] text-slate-600">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> P = PRO won round
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-400 ml-1" /> C = CON won round
                    </div>
                </div>
            </div>
        </div>
    );
}
