interface SparklineProps {
  data: number[];
  color?: string;
  height?: number;
  width?: number;
  fill?: boolean;
}

export default function SparklineChart({ data, color = '#3b82f6', height = 48, width = 120, fill = true }: SparklineProps) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pad = 4;
  const w = width - pad * 2;
  const h = height - pad * 2;
  const points = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * w;
    const y = pad + h - ((v - min) / range) * h;
    return `${x},${y}`;
  });
  const linePath = `M ${points.join(' L ')}`;
  const fillPath = `${linePath} L ${pad + w},${pad + h} L ${pad},${pad + h} Z`;

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
      <defs>
        <linearGradient id={`fill_${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {fill && (
        <path d={fillPath} fill={`url(#fill_${color.replace('#', '')})`} />
      )}
      <path d={linePath} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle
        cx={points[points.length - 1].split(',')[0]}
        cy={points[points.length - 1].split(',')[1]}
        r="3"
        fill={color}
        className="drop-shadow-sm"
      />
    </svg>
  );
}

interface BarChartProps {
  data: { label: string; value: number }[];
  color?: string;
  height?: number;
}

export function BarChart({ data, color = '#3b82f6', height = 120 }: BarChartProps) {
  if (!data || data.length === 0) return null;
  const max = Math.max(...data.map(d => d.value)) || 1;

  return (
    <div className="flex items-end gap-1" style={{ height }}>
      {data.map((d, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
          <div
            className="w-full rounded-t-sm transition-all duration-500 cursor-pointer"
            style={{
              height: `${(d.value / max) * (height - 20)}px`,
              backgroundColor: color,
              opacity: 0.7,
            }}
            title={`${d.label}: ${d.value}`}
          />
          <span className="text-[9px] text-slate-500 truncate w-full text-center">{d.label}</span>
        </div>
      ))}
    </div>
  );
}
