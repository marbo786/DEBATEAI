/**
 * BeliefChart — pure SVG animated belief trajectory chart.
 * No chart library required. Uses framer-motion for draw animation.
 *
 * Fixes applied:
 * - Hover tooltip shows "R1 PRO" / "R2 CON" not raw move index
 * - Turning point marker draws at the EXACT move with biggest swing
 *   (not always the CON move at end of round)
 */
import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface BeliefChartProps {
    beliefHistory: number[];   // 0.0–1.0, index 0 = prior, index n = after move n
    maxRounds: number;
    turningPointRound?: number | null;
    className?: string;
}

const W = 600;  // SVG viewBox width
const H = 180;  // SVG viewBox height
const PAD = { top: 16, right: 20, bottom: 32, left: 40 };

function toX(i: number, total: number): number {
    const innerW = W - PAD.left - PAD.right;
    return PAD.left + (total <= 1 ? innerW / 2 : (i / (total - 1)) * innerW);
}

function toY(belief: number): number {
    const innerH = H - PAD.top - PAD.bottom;
    return PAD.top + (1 - belief) * innerH;
}

function makePath(points: Array<[number, number]>): string {
    if (points.length < 2) return "";
    let d = `M ${points[0][0]} ${points[0][1]}`;
    for (let i = 1; i < points.length; i++) {
        const [x1, y1] = points[i - 1];
        const [x2, y2] = points[i];
        const cx = (x1 + x2) / 2;
        d += ` C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`;
    }
    return d;
}

function makeAreaPath(points: Array<[number, number]>): string {
    if (points.length < 2) return "";
    const mid = toY(0.5);
    const first = points[0];
    const last = points[points.length - 1];
    let d = `M ${first[0]} ${mid}`;
    d += ` L ${first[0]} ${first[1]}`;
    for (let i = 1; i < points.length; i++) {
        const [x1, y1] = points[i - 1];
        const [x2, y2] = points[i];
        const cx = (x1 + x2) / 2;
        d += ` C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`;
    }
    d += ` L ${last[0]} ${mid} Z`;
    return d;
}

/**
 * Given a belief_history index, return a human-readable label.
 * Index 0 = "Prior" (before any move).
 * Odd indices = PRO's turns, even indices (≥2) = CON's turns.
 * Round = ceil(idx / 2).
 */
function moveLabel(idx: number): string {
    if (idx === 0) return "Prior";
    const round = Math.ceil(idx / 2);
    const side = idx % 2 === 1 ? "PRO" : "CON";
    return `R${round} ${side}`;
}

export default function BeliefChart({
    beliefHistory,
    maxRounds,
    turningPointRound,
    className = "",
}: BeliefChartProps) {
    const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

    /**
     * Find the EXACT move index (within the turning point round) with the
     * largest single-move belief swing.
     * This is more precise than always drawing at `turningPointRound * 2`
     * (which picks the CON move regardless of which move caused the swing).
     */
    const turningPointMoveIdx = useMemo<number | null>(() => {
        if (!turningPointRound || !beliefHistory || beliefHistory.length < 2) return null;
        // Moves in round N are at belief_history indices: (N-1)*2+1 (PRO) and N*2 (CON)
        const startIdx = (turningPointRound - 1) * 2 + 1;
        const endIdx = Math.min(turningPointRound * 2, beliefHistory.length - 1);
        let maxSwing = 0;
        let bestIdx: number | null = null;
        for (let i = startIdx; i <= endIdx; i++) {
            const swing = Math.abs(beliefHistory[i] - beliefHistory[i - 1]);
            if (swing > maxSwing) {
                maxSwing = swing;
                bestIdx = i;
            }
        }
        return bestIdx;
    }, [turningPointRound, beliefHistory]);

    const points = useMemo<Array<[number, number]>>(() => {
        if (!beliefHistory || beliefHistory.length < 2) return [];
        return beliefHistory.map((b, i) => [toX(i, beliefHistory.length), toY(b)]);
    }, [beliefHistory]);

    const linePath = useMemo(() => makePath(points), [points]);
    const areaPath = useMemo(() => makeAreaPath(points), [points]);

    const midY = toY(0.5);
    const innerH = H - PAD.top - PAD.bottom;

    // X-axis labels: one per completed debate round (every 2 moves)
    const roundLabels = useMemo(() => {
        const rounds: Array<{ label: string; x: number }> = [];
        const n = beliefHistory.length;
        if (n < 2) return rounds;
        for (let i = 2; i < n; i += 2) {
            const roundNum = i / 2;
            rounds.push({ label: `R${roundNum}`, x: toX(i, n) });
        }
        return rounds;
    }, [beliefHistory, maxRounds]);

    if (points.length < 2) return null;

    const lastBelief = beliefHistory[beliefHistory.length - 1] ?? 0.5;
    const isProLeading = lastBelief > 0.5;

    return (
        <div className={`relative ${className}`}>
            <p className="text-[10px] font-bold tracking-widest text-slate-600 uppercase mb-2">
                Belief Trajectory
            </p>
            <div className="relative rounded-xl border border-white/[0.06] bg-slate-900/50 overflow-hidden">
                <svg
                    viewBox={`0 0 ${W} ${H}`}
                    className="w-full"
                    style={{ height: "140px" }}
                    onMouseLeave={() => setHoveredIdx(null)}
                >
                    <defs>
                        <linearGradient id="proGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
                            <stop offset="100%" stopColor="#10b981" stopOpacity="0.02" />
                        </linearGradient>
                        <linearGradient id="conGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.02" />
                            <stop offset="100%" stopColor="#f43f5e" stopOpacity="0.3" />
                        </linearGradient>
                        <clipPath id="aboveMid">
                            <rect x="0" y="0" width={W} height={midY} />
                        </clipPath>
                        <clipPath id="belowMid">
                            <rect x="0" y={midY} width={W} height={H - midY} />
                        </clipPath>
                        <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
                            <stop offset="0%" stopColor={isProLeading ? "#34d399" : "#fb7185"} stopOpacity="0.6" />
                            <stop offset="100%" stopColor={isProLeading ? "#10b981" : "#f43f5e"} />
                        </linearGradient>
                    </defs>

                    {/* Background grid lines */}
                    {[0, 0.25, 0.5, 0.75, 1].map((v) => {
                        const y = toY(v);
                        const isMid = v === 0.5;
                        return (
                            <line
                                key={v}
                                x1={PAD.left} y1={y} x2={W - PAD.right} y2={y}
                                stroke={isMid ? "#334155" : "#1e293b"}
                                strokeWidth={isMid ? 1.5 : 0.8}
                                strokeDasharray={isMid ? undefined : "3 5"}
                            />
                        );
                    })}

                    {/* Turning point vertical marker — at the EXACT move with the biggest swing */}
                    {turningPointMoveIdx !== null && turningPointMoveIdx < points.length && (
                        <line
                            x1={points[turningPointMoveIdx][0]}
                            y1={PAD.top}
                            x2={points[turningPointMoveIdx][0]}
                            y2={H - PAD.bottom}
                            stroke="#f59e0b"
                            strokeWidth={1.5}
                            strokeDasharray="4 3"
                            opacity={0.6}
                        />
                    )}

                    {/* Area fill — above midline (pro territory) */}
                    <motion.path
                        d={areaPath}
                        fill="url(#proGrad)"
                        clipPath="url(#aboveMid)"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.6, delay: 0.3 }}
                    />
                    {/* Area fill — below midline (con territory) */}
                    <motion.path
                        d={areaPath}
                        fill="url(#conGrad)"
                        clipPath="url(#belowMid)"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.6, delay: 0.3 }}
                    />

                    {/* Animated bezier line — re-animates when new point added */}
                    <motion.path
                        key={beliefHistory.length}
                        d={linePath}
                        fill="none"
                        stroke="url(#lineGrad)"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        initial={{ pathLength: 0, opacity: 0 }}
                        animate={{ pathLength: 1, opacity: 1 }}
                        transition={{ duration: 0.8, ease: "easeOut" }}
                    />

                    {/* Y-axis labels */}
                    {[{ v: 1, label: "100%" }, { v: 0.5, label: "50%" }, { v: 0, label: "0%" }].map(({ v, label }) => (
                        <text key={v} x={PAD.left - 4} y={toY(v) + 4} textAnchor="end" fontSize="9" fill="#475569">
                            {label}
                        </text>
                    ))}

                    {/* X-axis round labels */}
                    {roundLabels.map(({ label, x }) => (
                        <text
                            key={label}
                            x={x}
                            y={H - PAD.bottom + 14}
                            textAnchor="middle"
                            fontSize="9"
                            fill="#334155"
                        >
                            {label}
                        </text>
                    ))}

                    {/* Hover interaction layer + dots */}
                    {points.map(([x, y], i) => {
                        const isHovered = hoveredIdx === i;
                        const belief = beliefHistory[i];
                        // Turning point dot gets amber highlight
                        const isTurningPt = i === turningPointMoveIdx;
                        return (
                            <g key={i}>
                                <rect
                                    x={x - 12} y={PAD.top} width={24} height={innerH}
                                    fill="transparent"
                                    onMouseEnter={() => setHoveredIdx(i)}
                                />
                                <motion.circle
                                    cx={x} cy={y}
                                    r={isHovered ? 5 : isTurningPt ? 4 : 3}
                                    fill={isTurningPt && !isHovered
                                        ? "#f59e0b"
                                        : belief > 0.5 ? "#10b981"
                                            : belief < 0.5 ? "#f43f5e"
                                                : "#94a3b8"}
                                    stroke={isHovered ? "white" : "transparent"}
                                    strokeWidth={1.5}
                                    animate={{ r: isHovered ? 5 : isTurningPt ? 4 : 3 }}
                                    transition={{ duration: 0.15 }}
                                />
                            </g>
                        );
                    })}

                    {/* Hover tooltip */}
                    <AnimatePresence>
                        {hoveredIdx !== null && (() => {
                            const [x, y] = points[hoveredIdx];
                            const belief = beliefHistory[hoveredIdx];
                            const label = moveLabel(hoveredIdx);
                            const pct = Math.round(belief * 100);
                            const tooltipX = x > W - 90 ? x - 80 : x + 8;
                            return (
                                <motion.g
                                    key={hoveredIdx}
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0 }}
                                    transition={{ duration: 0.1 }}
                                >
                                    <rect
                                        x={tooltipX} y={y - 22} width={72} height={20}
                                        rx={4}
                                        fill="#0f172a"
                                        stroke="#334155"
                                        strokeWidth={0.8}
                                    />
                                    <text x={tooltipX + 6} y={y - 8} fontSize="9" fill="#94a3b8">
                                        {label}
                                    </text>
                                    <text
                                        x={tooltipX + 66} y={y - 8}
                                        fontSize="9"
                                        fontWeight="bold"
                                        fill={belief > 0.5 ? "#34d399" : belief < 0.5 ? "#fb7185" : "#94a3b8"}
                                        textAnchor="end"
                                    >
                                        {pct}%
                                    </text>
                                </motion.g>
                            );
                        })()}
                    </AnimatePresence>
                </svg>

                {/* Legend */}
                <div className="absolute top-2 right-3 flex items-center gap-3 text-[9px] text-slate-500">
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 opacity-80" /> Pro
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-rose-500 opacity-80" /> Con
                    </span>
                    {turningPointMoveIdx !== null && (
                        <span className="flex items-center gap-1">
                            <span className="inline-block w-3 bg-amber-400 opacity-70" style={{ height: "2px" }} />
                            {moveLabel(turningPointMoveIdx)}
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}
