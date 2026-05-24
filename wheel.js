// ═══════════════════════════════════════════════════════════════════════════
//  نظام عجلة الروليت الاحترافية - كرة حقيقية + عجلة مسطحة + Supabase
// ═══════════════════════════════════════════════════════════════════════════

const API_BASE = window.location.origin;
const PARAMS = new URLSearchParams(window.location.search);
const tg = window.Telegram?.WebApp;
const IS_TELEGRAM_WEBAPP = Boolean(tg);

if (IS_TELEGRAM_WEBAPP) {
    tg.ready();
    tg.expand();
}

const USER_ID = PARAMS.get('user_id')
    || (IS_TELEGRAM_WEBAPP && tg.initDataUnsafe?.user?.id
        ? String(tg.initDataUnsafe.user.id)
        : null);

let pendingSpinPayload = null;

const wheel = document.querySelector('.wheel');
const startButton = document.querySelector('.button');
const resultBox = document.getElementById('result_box');
const trialSpinPanel = document.getElementById('trial-spin-panel');
const trialSpinButton = document.getElementById('trial-spin-btn');
const gameContainer = document.getElementById('game');
const wheelCanvas = document.getElementById('wheelCanvas');
const wheelCtx = wheelCanvas.getContext('2d');
const rouletteBall = document.getElementById('rouletteBall');

const initialWheelConfig = JSON.parse(document.getElementById('wheel-config-data')?.textContent || '{}');

let wheelConfig = {};
let wheelSegments = [];

let deg = 0;
let landingDeg = 0;
let currentWheelRotation = 0;
let win_type = 0;
let winned = 0;
let cad_text = '';
let chance = '';
let rewardType = '';
let isWheelSpinning = false;
let isTrialSpinActive = false;
let pendingWheelResize = false;
let wheelResizeFrameId = null;

// ── حالة كرة الروليت ──
let ballPhase = 'idle';
let ballAngle = -Math.PI / 2;
let ballRadius = 0;
let ballDecelFrom = 0;
let ballDecelTarget = null;
let ballDecelT0 = 0, ballDecelDur = 0;
let ballSpinStartT = 0;
let ballPendingResult = null;
let ballTrail = [];
const BALL_TRAIL_LEN = 16;
const BALL_THROW_DUR = 540;

// ── تحميل خطوط العجلة ──
const _SYSTEM_FONTS = new Set(['cairo','arial','tahoma','verdana','trebuchet ms','georgia',
                                 'times new roman','courier new','sans-serif','serif']);
const _loadedFonts = new Set();
const _loadingFonts = new Map();

let _fontsListCache = null;
async function _fetchFontsList() {
    if (_fontsListCache) return _fontsListCache;
    try {
        const res = await fetch('/api/wheel/fonts');
        const data = await res.json();
        _fontsListCache = data.fonts || [];
    } catch(e) { _fontsListCache = []; }
    return _fontsListCache;
}

async function ensureWheelFont(family, directUrl) {
    if (!family || _SYSTEM_FONTS.has(family.toLowerCase())) return;
    if (_loadedFonts.has(family)) return;
    if (_loadingFonts.has(family)) { return _loadingFonts.get(family); }

    const promise = (async () => {
        let url = directUrl;
        if (!url) {
            const list = await _fetchFontsList();
            const match = list.find(f => f.file.replace(/\.(ttf|otf|woff2?)$/i, '') === family);
            url = match ? match.url : null;
        }
        if (!url) return;
        const styleId = `wf-${family.replace(/\W/g,'_')}`;
        if (!document.getElementById(styleId)) {
            const fmt = url.match(/\.woff2$/i) ? 'woff2'
                       : url.match(/\.woff$/i) ? 'woff'
                       : url.match(/\.otf$/i) ? 'opentype' : 'truetype';
            const st = document.createElement('style');
            st.id = styleId;
            st.textContent = `@font-face{font-family:'${family}';src:url('${url}') format('${fmt}');font-display:block;}`;
            document.head.appendChild(st);
        }
        try {
            const face = new FontFace(family, `url(${url})`);
            const loaded = await face.load();
            document.fonts.add(loaded);
            _loadedFonts.add(family);
        } catch(e) {
            _loadedFonts.add(family);
            console.warn('[wheel] FontFace load warning:', family, e);
        }
    })();

    _loadingFonts.set(family, promise);
    await promise;
    _loadingFonts.delete(family);
}

// ── إعدادات العجلة ──
function loadWheelConfigFromDom() {
    wheelConfig = initialWheelConfig || {};
    wheelSegments = Array.isArray(wheelConfig.segments) ? wheelConfig.segments : [];
    const rootStyle = document.documentElement.style;
    rootStyle.setProperty('--wheel-border-color', wheelConfig.wheel_border_color || '#ffdd91');
    rootStyle.setProperty('--segment-border-color', wheelConfig.segment_border_color || '#ffffff');
    rootStyle.setProperty('--wheel-button-color', wheelConfig.wheel_button_color || '#fa513e');

    const ff = wheelConfig.segment_text_font_family;
    if (ff && !_SYSTEM_FONTS.has(ff.toLowerCase())) {
        ensureWheelFont(ff).then(() => drawWheel());
    }
    updateTrialSpinPanelVisibility();
}

function getSegmentGlowIntensity() {
    return clamp(Number(wheelConfig.segment_glow_intensity ?? 1), 0, 2);
}

function getSegmentAngle() {
    if (!wheelSegments.length) return 360;
    return 360 / wheelSegments.length;
}

function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

function hexToRgb(hex) {
    const safeHex = String(hex || '').replace('#', '').trim();
    if (safeHex.length !== 6) return { r: 52, g: 152, b: 219 };
    return {
        r: parseInt(safeHex.slice(0, 2), 16),
        g: parseInt(safeHex.slice(2, 4), 16),
        b: parseInt(safeHex.slice(4, 6), 16),
    };
}

function shadeColor(hex, factor) {
    const rgb = hexToRgb(hex);
    const adjust = (channel) => clamp(Math.round(channel + ((factor >= 0 ? 255 - channel : channel) * factor)), 0, 255);
    return `rgb(${adjust(rgb.r)}, ${adjust(rgb.g)}, ${adjust(rgb.b)})`;
}

function rgbaColor(color, alpha) {
    const match = String(color || '').match(/\d+/g);
    if (!match || match.length < 3) return `rgba(255, 255, 255, ${alpha})`;
    return `rgba(${match[0]}, ${match[1]}, ${match[2]}, ${alpha})`;
}

// محرّك ألوان HSL
function hexToHsl(hex) {
    const c = hexToRgb(hex);
    const r = c.r/255, g = c.g/255, b = c.b/255;
    const max = Math.max(r,g,b), min = Math.min(r,g,b);
    let h = 0, s = 0, l = (max+min)/2;
    if (max !== min) {
        const d = max - min;
        s = l > 0.5 ? d/(2-max-min) : d/(max+min);
        if (max===r) h = ((g-b)/d + (g<b?6:0))/6;
        else if (max===g) h = ((b-r)/d + 2)/6;
        else h = ((r-g)/d + 4)/6;
    }
    return [h*360, s*100, l*100];
}

function hslStr(h, s, l) {
    h = ((h%360)+360)%360;
    s = Math.max(0, Math.min(100, s));
    l = Math.max(0, Math.min(100, l));
    const hN = h/360, sN = s/100, lN = l/100;
    const q = lN<0.5 ? lN*(1+sN) : lN+sN-lN*sN, p = 2*lN-q;
    const ch = (t) => {
        t = ((t%1)+1)%1;
        if (t<1/6) return p+(q-p)*6*t;
        if (t<1/2) return q;
        if (t<2/3) return p+(q-p)*(2/3-t)*6;
        return p;
    };
    return `rgb(${Math.round(ch(hN+1/3)*255)},${Math.round(ch(hN)*255)},${Math.round(ch(hN-1/3)*255)})`;
}

function warmHighlight(hex, boost) {
    const [h, s, l] = hexToHsl(hex);
    return hslStr(h+11*boost, Math.min(100, s*1.10), Math.min(93, l+40*boost));
}

function coolShadow(hex, depth) {
    const [h, s, l] = hexToHsl(hex);
    return hslStr(h-16*depth, Math.max(18, s*0.70), Math.max(3, l*(1-0.55*depth)));
}

function richMid(hex) {
    const [h, s, l] = hexToHsl(hex);
    return hslStr(h+4, Math.min(100, s*1.20), l);
}

function getSegmentTextStyle() {
    return {
        color: wheelConfig.segment_text_color || '#ffffff',
        strokeColor: wheelConfig.segment_text_stroke_color || '#101828',
        fontFamily: wheelConfig.segment_text_font_family || 'Trebuchet MS',
        fontWeight: String(wheelConfig.segment_text_font_weight || '700'),
        sizeScale: clamp(Number(wheelConfig.segment_text_size_scale ?? 1), 0.7, 3.0),
        strokeWidth: clamp(Number(wheelConfig.segment_text_stroke_width ?? 0.12), 0, 0.35),
    };
}

function wrapLabel(label, maxCharsPerLine = 11, maxLines = 3) {
    const words = String(label || '').trim().split(/\s+/).filter(Boolean);
    if (!words.length) return [''];
    const lines = [];
    let currentLine = '';
    words.forEach((word) => {
        const candidate = currentLine ? `${currentLine} ${word}` : word;
        if (candidate.length <= maxCharsPerLine || !currentLine) {
            currentLine = candidate;
        } else {
            lines.push(currentLine);
            currentLine = word;
        }
    });
    if (currentLine) lines.push(currentLine);
    if (lines.length > maxLines) {
        const trimmed = lines.slice(0, maxLines);
        trimmed[maxLines - 1] = `${trimmed[maxLines - 1].slice(0, Math.max(3, maxCharsPerLine - 3))}...`;
        return trimmed;
    }
    return lines;
}

function traceSegmentPath(ctx, radius, startAngle, endAngle) {
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.arc(0, 0, radius, startAngle, endAngle);
    ctx.closePath();
}

function drawSegmentLabel(ctx, segment, width, radius, startAngle, anglePerSegment) {
    ctx.save();
    const textAngle = startAngle + (anglePerSegment / 2);
    const textStyle = getSegmentTextStyle();
    const displayMode = String(segment.display_mode || 'text');
    const icon = String(segment.icon || '').trim();
    const showIcon = displayMode === 'icon' || displayMode === 'icon_text';
    const showText = displayMode === 'text' || displayMode === 'icon_text' || !showIcon;
    const radialBase = clamp(Number(wheelConfig.segment_text_radial_position ?? 0.60), 0.30, 0.90);
    const radialPosition = radius * (showIcon && showText ? radialBase - 0.02 : radialBase);
    const lines = showText ? wrapLabel(segment.label || '', anglePerSegment < 0.75 ? 8 : 12, anglePerSegment < 0.75 ? 3 : 2) : [];
    const fontSize = clamp(width * (anglePerSegment < 0.75 ? 0.021 : 0.026) * textStyle.sizeScale, 10, 80);
    const iconSize = clamp(fontSize * (showText ? 1.22 : 1.8), 14, 42);
    const lineHeight = fontSize * 1.08;

    ctx.rotate(textAngle);
    ctx.translate(radialPosition, 0);
    ctx.rotate(Math.PI / 2);

    ctx.font = `${textStyle.fontWeight} ${fontSize}px "${textStyle.fontFamily}", Arial, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.lineWidth = Math.max(0, fontSize * textStyle.strokeWidth);
    ctx.strokeStyle = textStyle.strokeColor;
    ctx.fillStyle = textStyle.color;
    ctx.shadowColor = 'rgba(0, 0, 0, 0.38)';
    ctx.shadowBlur = 14;

    if (showIcon && icon) {
        ctx.font = `${textStyle.fontWeight} ${iconSize}px "${textStyle.fontFamily}", Arial, sans-serif`;
        const iconY = showText ? -(lineHeight * 0.95) : 0;
        if (ctx.lineWidth > 0) ctx.strokeText(icon, 0, iconY);
        ctx.fillText(icon, 0, iconY);
    }

    if (showText && lines.length) {
        ctx.font = `${textStyle.fontWeight} ${fontSize}px "${textStyle.fontFamily}", Arial, sans-serif`;
        const startY = showIcon && icon ? 0 : -((lines.length - 1) * lineHeight) / 2;
        lines.forEach((line, index) => {
            const y = startY + (index * lineHeight);
            if (ctx.lineWidth > 0) ctx.strokeText(line, 0, y);
            ctx.fillText(line, 0, y);
        });
    }
    ctx.restore();
}

function normalizeRotationDegrees(rotation) {
    const normalized = Number(rotation) % 360;
    return normalized < 0 ? normalized + 360 : normalized;
}

function getSpinFullTurns() {
    return clamp(Number(wheelConfig.spin_full_turns ?? wheelConfig.min_spin_turns ?? 6), 4, 12);
}

function buildVisualSpinTarget(targetRotation) {
    const normalizedTarget = normalizeRotationDegrees(targetRotation);
    const normalizedCurrent = normalizeRotationDegrees(currentWheelRotation);
    let delta = normalizedTarget - normalizedCurrent;
    if (delta < 0) delta += 360;
    const extraTurn = delta < 120 ? 360 : 0;
    return currentWheelRotation + (getSpinFullTurns() * 360) + extraTurn + delta;
}

function applyWheelRotation(rotation) {
    wheel.style.transform = `rotate(${rotation}deg)`;
}

// ── رسم العجلة ──
function drawWheel() {
    if (!wheelCtx) return;
    if (!wheelSegments.length) {
        wheelCtx.clearRect(0, 0, wheelCanvas.width, wheelCanvas.height);
        return;
    }

    const width = wheelCanvas.width;
    const height = wheelCanvas.height;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const logicalWidth = width / dpr;
    const logicalHeight = height / dpr;
    wheelCtx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const centerX = logicalWidth / 2;
    const centerY = logicalHeight / 2;
    const radius = Math.min(centerX, centerY) - 12;
    const anglePerSegment = (Math.PI * 2) / wheelSegments.length;

    wheelCtx.clearRect(0, 0, logicalWidth, logicalHeight);

    // توهج خارجي
    const outerGlow = wheelCtx.createRadialGradient(centerX, centerY, radius * 0.1, centerX, centerY, radius * 1.22);
    outerGlow.addColorStop(0, 'rgba(255,255,255,0.06)');
    outerGlow.addColorStop(0.55, 'rgba(255,255,255,0.02)');
    outerGlow.addColorStop(1, 'rgba(0,0,0,0.24)');
    wheelCtx.fillStyle = outerGlow;
    wheelCtx.beginPath();
    wheelCtx.arc(centerX, centerY, radius * 1.16, 0, Math.PI * 2);
    wheelCtx.fill();

    wheelCtx.save();
    wheelCtx.translate(centerX, centerY);

    // قرص العجلة
    wheelCtx.beginPath();
    wheelCtx.arc(0, 0, radius + 4, 0, Math.PI * 2);
    const baseDisc = wheelCtx.createRadialGradient(0, 0, radius * 0.1, 0, 0, radius + 4);
    baseDisc.addColorStop(0, 'rgba(255,255,255,0.10)');
    baseDisc.addColorStop(1, 'rgba(15,23,42,0.92)');
    wheelCtx.fillStyle = baseDisc;
    wheelCtx.fill();

    // القطاعات
    wheelSegments.forEach((segment, index) => {
        const startAngle = (-Math.PI / 2) + (index * anglePerSegment);
        const endAngle = startAngle + anglePerSegment;
        const midAngle = startAngle + (anglePerSegment / 2);
        const baseColor = segment.color || '#3498db';
        const hasEndColor = Boolean(segment.color_end);
        const endColor = hasEndColor ? segment.color_end : baseColor;
        const glowIntensity = getSegmentGlowIntensity();

        const warm1 = warmHighlight(baseColor, 0.88);
        const warm2 = warmHighlight(baseColor, 0.44);
        const richColor = richMid(baseColor);
        const srcShd = hasEndColor ? endColor : baseColor;
        const cool1 = coolShadow(srcShd, 0.46);
        const cool2 = coolShadow(srcShd, 0.88);

        // قاعدة معدنية
        traceSegmentPath(wheelCtx, radius, startAngle, endAngle);
        const baseGrad = wheelCtx.createRadialGradient(0, 0, radius * 0.06, 0, 0, radius * 1.01);
        baseGrad.addColorStop(0, warm2);
        baseGrad.addColorStop(0.22, warm1);
        baseGrad.addColorStop(0.50, richColor);
        baseGrad.addColorStop(0.76, cool1);
        baseGrad.addColorStop(1, cool2);
        wheelCtx.fillStyle = baseGrad;
        wheelCtx.fill();

        // إضاءة اتجاهية
        const litX = Math.cos(midAngle - 0.42) * radius * 0.30;
        const litY = Math.sin(midAngle - 0.42) * radius * 0.30;
        const shdX = Math.cos(midAngle + Math.PI * 0.68) * radius * 0.52;
        const shdY = Math.sin(midAngle + Math.PI * 0.68) * radius * 0.52;
        traceSegmentPath(wheelCtx, radius, startAngle, endAngle);
        const domeGrad = wheelCtx.createLinearGradient(litX, litY, shdX, shdY);
        domeGrad.addColorStop(0, 'rgba(255,255,255,0.30)');
        domeGrad.addColorStop(0.24, 'rgba(255,255,255,0.11)');
        domeGrad.addColorStop(0.54, 'rgba(0,0,0,0.02)');
        domeGrad.addColorStop(1, 'rgba(0,0,0,0.22)');
        wheelCtx.fillStyle = domeGrad;
        wheelCtx.fill();

        // بريق كريستالي
        const spX = Math.cos(midAngle - 0.50) * radius * 0.27;
        const spY = Math.sin(midAngle - 0.50) * radius * 0.27;
        wheelCtx.save();
        traceSegmentPath(wheelCtx, radius * 0.76, startAngle + anglePerSegment * 0.05, endAngle - anglePerSegment * 0.05);
        wheelCtx.clip();
        const specGrad = wheelCtx.createRadialGradient(spX, spY, 0, spX, spY, radius * 0.58);
        specGrad.addColorStop(0, 'rgba(255,255,255,0.72)');
        specGrad.addColorStop(0.14, 'rgba(255,255,255,0.38)');
        specGrad.addColorStop(0.40, 'rgba(255,255,255,0.10)');
        specGrad.addColorStop(0.72, 'rgba(255,255,255,0.02)');
        specGrad.addColorStop(1, 'rgba(255,255,255,0)');
        wheelCtx.fillStyle = specGrad;
        wheelCtx.globalAlpha = 0.88;
        wheelCtx.fill();
        wheelCtx.restore();

        // ظل عمق الحافة
        wheelCtx.save();
        traceSegmentPath(wheelCtx, radius, startAngle, endAngle);
        wheelCtx.clip();
        const rimDepth = wheelCtx.createRadialGradient(0, 0, radius * 0.68, 0, 0, radius);
        rimDepth.addColorStop(0, 'rgba(0,0,0,0)');
        rimDepth.addColorStop(0.70, 'rgba(0,0,0,0)');
        rimDepth.addColorStop(0.86, 'rgba(0,0,0,0.06)');
        rimDepth.addColorStop(1, 'rgba(0,0,0,0.34)');
        wheelCtx.fillStyle = rimDepth;
        wheelCtx.fill();
        wheelCtx.restore();

        // حدود معدنية
        if (wheelConfig.segment_border_enabled !== false) {
            const borderHex = wheelConfig.segment_border_color || '#ffffff';
            traceSegmentPath(wheelCtx, radius, startAngle, endAngle);
            wheelCtx.lineJoin = 'round';
            wheelCtx.lineWidth = Math.max(2.5, logicalWidth * 0.0088);
            wheelCtx.strokeStyle = rgbaColor(shadeColor(borderHex, -0.12), 0.44);
            wheelCtx.stroke();
            traceSegmentPath(wheelCtx, radius * 0.992, startAngle + 0.007, endAngle - 0.007);
            wheelCtx.lineWidth = Math.max(1.2, logicalWidth * 0.0040);
            wheelCtx.strokeStyle = rgbaColor(shadeColor(borderHex, 0.55), 0.52);
            wheelCtx.stroke();
        }

        // توهج
        if (glowIntensity > 0) {
            wheelCtx.save();
            wheelCtx.globalCompositeOperation = 'lighter';
            wheelCtx.lineJoin = 'round';
            wheelCtx.lineCap = 'round';
            traceSegmentPath(wheelCtx, radius * 0.996, startAngle, endAngle);
            wheelCtx.lineWidth = Math.max(3, logicalWidth * (0.008 + 0.004 * glowIntensity));
            wheelCtx.strokeStyle = rgbaColor(shadeColor(baseColor, 0.62), 0.22 + 0.24 * glowIntensity);
            wheelCtx.shadowColor = rgbaColor(shadeColor(baseColor, 0.88), 0.32 + 0.46 * glowIntensity);
            wheelCtx.shadowBlur = Math.max(8, logicalWidth * (0.010 + 0.012 * glowIntensity));
            wheelCtx.stroke();
            traceSegmentPath(wheelCtx, radius * 0.986, startAngle + 0.003, endAngle - 0.003);
            wheelCtx.lineWidth = Math.max(1.1, logicalWidth * (0.002 + 0.0015 * glowIntensity));
            wheelCtx.strokeStyle = `rgba(255,255,255,${0.16 + 0.26 * glowIntensity})`;
            wheelCtx.shadowBlur = 0;
            wheelCtx.stroke();
            wheelCtx.restore();
        }

        drawSegmentLabel(wheelCtx, segment, logicalWidth, radius, startAngle, anglePerSegment);
    });

    // إطار العجلة
    const borderThickness = clamp(Number(wheelConfig.wheel_border_thickness ?? 8), 0, 24);
    if (borderThickness > 0) {
        const borderGlowIntensity = clamp(Number(wheelConfig.wheel_border_glow_intensity ?? 1), 0, 4);
        const borderHex = wheelConfig.wheel_border_color || '#ffdd91';
        wheelCtx.beginPath();
        wheelCtx.arc(0, 0, radius * 1.01, 0, Math.PI * 2);
        wheelCtx.lineWidth = Math.max(borderThickness, logicalWidth * (0.012 + borderThickness / 1000));
        wheelCtx.strokeStyle = shadeColor(borderHex, 0.05);
        wheelCtx.shadowColor = rgbaColor(shadeColor(borderHex, 0.15), 0.26 + 0.40 * borderGlowIntensity);
        wheelCtx.shadowBlur = Math.max(6, logicalWidth * (0.010 + 0.020 * borderGlowIntensity));
        wheelCtx.stroke();
        wheelCtx.shadowBlur = 0;
        wheelCtx.beginPath();
        wheelCtx.arc(0, 0, radius * 1.01 - borderThickness * 0.46, 0, Math.PI * 2);
        wheelCtx.lineWidth = Math.max(1, logicalWidth * 0.0028);
        wheelCtx.strokeStyle = rgbaColor(shadeColor(borderHex, 0.72), 0.50);
        wheelCtx.stroke();
        wheelCtx.beginPath();
        wheelCtx.arc(0, 0, radius * 1.01 + borderThickness * 0.28, 0, Math.PI * 2);
        wheelCtx.lineWidth = Math.max(1.5, logicalWidth * 0.004);
        wheelCtx.strokeStyle = 'rgba(0,0,0,0.28)';
        wheelCtx.stroke();
    }

    // زر المركز
    wheelCtx.shadowBlur = 0;
    const btnColor = wheelConfig.wheel_button_color || '#fa513e';

    wheelCtx.beginPath();
    wheelCtx.arc(0, 0, radius * 0.225, 0, Math.PI * 2);
    const ringGrad = wheelCtx.createRadialGradient(-radius*0.06, -radius*0.07, 0, 0, 0, radius*0.225);
    ringGrad.addColorStop(0, 'rgba(255,255,255,0.68)');
    ringGrad.addColorStop(0.42, 'rgba(255,255,255,0.24)');
    ringGrad.addColorStop(1, 'rgba(0,0,0,0.50)');
    wheelCtx.fillStyle = ringGrad;
    wheelCtx.fill();

    wheelCtx.beginPath();
    wheelCtx.arc(0, 0, radius * 0.183, 0, Math.PI * 2);
    const btnGrad = wheelCtx.createRadialGradient(-radius*0.048, -radius*0.068, radius*0.01, 0, 0, radius*0.19);
    btnGrad.addColorStop(0, warmHighlight(btnColor, 0.82));
    btnGrad.addColorStop(0.28, warmHighlight(btnColor, 0.36));
    btnGrad.addColorStop(0.65, richMid(btnColor));
    btnGrad.addColorStop(1, coolShadow(btnColor, 0.50));
    wheelCtx.fillStyle = btnGrad;
    wheelCtx.fill();

    wheelCtx.save();
    wheelCtx.beginPath();
    wheelCtx.arc(0, 0, radius * 0.183, 0, Math.PI * 2);
    wheelCtx.clip();
    const btnGloss = wheelCtx.createRadialGradient(-radius*0.044, -radius*0.072, 0, -radius*0.018, -radius*0.038, radius*0.152);
    btnGloss.addColorStop(0, 'rgba(255,255,255,0.78)');
    btnGloss.addColorStop(0.36, 'rgba(255,255,255,0.30)');
    btnGloss.addColorStop(0.72, 'rgba(255,255,255,0.06)');
    btnGloss.addColorStop(1, 'rgba(255,255,255,0)');
    wheelCtx.fillStyle = btnGloss;
    wheelCtx.fill();
    wheelCtx.restore();

    wheelCtx.beginPath();
    wheelCtx.arc(0, 0, radius * 0.183, 0, Math.PI * 2);
    wheelCtx.lineWidth = Math.max(3.5, logicalWidth * 0.011);
    wheelCtx.strokeStyle = 'rgba(255,255,255,0.84)';
    wheelCtx.stroke();

    wheelCtx.restore();
}

// ── نظام كرة الروليت ──
function easeOutCubic(t) { return 1 - Math.pow(1-t, 3); }
function easeOutQuart(t) { return 1 - Math.pow(1-t, 4); }
function easeInOutSine(t) { return -(Math.cos(Math.PI*t)-1)*.5; }

function updateBallPosition() {
    if (ballPhase === 'idle') return;

    const gameRect = gameContainer.getBoundingClientRect();
    const cx = gameRect.width / 2;
    const cy = gameRect.height / 2;
    const rimR = Math.min(gameRect.width, gameRect.height) / 2 - 12;
    const maxR = rimR - 7;

    let bx, by;

    if (ballPhase === 'throw') {
        const tp = Math.min((performance.now() - ballSpinStartT) / BALL_THROW_DUR, 1);
        const te = easeOutCubic(tp);

        const sx = cx + gameRect.width * 0.20;
        const sy = gameRect.height * 0.03;
        const ex = cx + Math.cos(-Math.PI/2) * maxR;
        const ey = cy + Math.sin(-Math.PI/2) * maxR;
        const cpx = cx - gameRect.width * 0.08;
        const cpy = gameRect.height * 0.09;

        const q = te;
        bx = (1-q)*(1-q)*sx + 2*(1-q)*q*cpx + q*q*ex;
        by = (1-q)*(1-q)*sy + 2*(1-q)*q*cpy + q*q*ey;

        if (tp >= 1) {
            ballPhase = 'orbit';
            ballAngle = -Math.PI/2;
            ballRadius = maxR;
        }
    } else if (ballPhase === 'orbit') {
        ballAngle -= 0.112;
        ballRadius = maxR;
        bx = cx + Math.cos(ballAngle) * ballRadius;
        by = cy + Math.sin(ballAngle) * ballRadius;
    } else if (ballPhase === 'decel' && ballDecelTarget !== null) {
        const elapsed = performance.now() - ballDecelT0;
        const progress = Math.min(elapsed / ballDecelDur, 1);
        const eased = easeOutQuart(progress);
        ballAngle = ballDecelFrom + (ballDecelTarget - ballDecelFrom) * eased;

        const dropP = Math.max(0, (progress - 0.80) / 0.20);
        const dropE = easeInOutSine(dropP);
        const bounce = Math.sin(dropP * Math.PI * 7) * rimR * .038 * (1 - dropP);
        ballRadius = maxR - (maxR - rimR * .60) * dropE + bounce;

        bx = cx + Math.cos(ballAngle) * ballRadius;
        by = cy + Math.sin(ballAngle) * ballRadius;
    }

    if (bx !== undefined && by !== undefined) {
        rouletteBall.style.left = `${bx - 7}px`;
        rouletteBall.style.top = `${by - 7}px`;
    }

    if (ballPhase !== 'idle') {
        requestAnimationFrame(updateBallPosition);
    }
}

function setBallResult(winnerIdx, spinMs) {
    const pinAngle = -Math.PI/2;
    const currMod = ((ballAngle % (Math.PI*2)) + Math.PI*2) % (Math.PI*2);
    const pinMod = ((pinAngle % (Math.PI*2)) + Math.PI*2) % (Math.PI*2);

    let delta = pinMod - currMod;
    if (delta > 0) delta -= Math.PI*2;
    const totalDelta = delta - 4 * Math.PI*2;

    const elapsed = performance.now() - ballSpinStartT;
    const remaining = Math.max(spinMs - elapsed, 1200);

    ballDecelFrom = ballAngle;
    ballDecelTarget = ballAngle + totalDelta;
    ballDecelT0 = performance.now();
    ballDecelDur = remaining;
    ballPhase = 'decel';
}

// ── إمالة العجلة ──
function tiltWheel() {
    gameContainer.classList.add('tilted');
    ballPhase = 'throw';
    ballSpinStartT = performance.now();
    updateBallPosition();
}

function untiltWheel() {
    gameContainer.classList.remove('tilted');
    ballPhase = 'idle';
    ballDecelTarget = null;
}

// ── حالة الزر ──
function updateButtonState() {
    const has_free_spin = document.getElementById('has_free_spin').value;
    if (has_free_spin === 'True') {
        startButton.style.pointerEvents = 'auto';
        startButton.classList.remove('disabled');
    } else {
        startButton.style.pointerEvents = 'none';
        startButton.classList.add('disabled');
    }
}

function isTrialSpinEnabled() {
    return !previewMode && wheelConfig.show_trial_spin_button !== false && 
           Array.isArray(wheelSegments) && wheelSegments.length > 0;
}

function updateTrialSpinPanelVisibility(forceHide = false) {
    if (!trialSpinPanel) return;
    const shouldShow = !forceHide && !isWheelSpinning && isTrialSpinEnabled();
    trialSpinPanel.style.display = shouldShow ? 'block' : 'none';
}

// ── عرض النتيجة ──
function showResult() {
    resultBox.style.display = 'block';
    resultBox.innerText = cad_text;

    if (rewardType === 'respin') {
        resultBox.className = 'respin-result';
    } else if (rewardType === 'trial') {
        resultBox.className = 'trial-result';
    } else if (winned === 1) {
        resultBox.className = 'win-result celebration-text';
    } else {
        resultBox.className = 'lose-result';
    }
}

function showWheelStoppedMessage(message, type = 'stopped') {
    resultBox.style.display = 'block';
    resultBox.innerText = message;
    resultBox.className = type === 'error' ? 'lose-result' : 'wheel-stopped-result';
    setTimeout(() => {
        resultBox.style.display = 'none';
        resultBox.className = '';
    }, 5000);
}

function showMsg(text, isError = true) {
    const msgBox = document.getElementById('msgBox');
    msgBox.textContent = text;
    msgBox.style.background = isError ? 'rgba(200,30,30,0.9)' : 'rgba(30,150,30,0.9)';
    msgBox.style.display = 'block';
    setTimeout(() => { msgBox.style.display = 'none'; }, 3000);
}

// ── التحقق من Supabase ──
function sendPrizeToTelegramBot(result, label) {
    if (!IS_TELEGRAM_WEBAPP || !result) return;
    try {
        tg.sendData(JSON.stringify({
            prize: {
                type: result.type,
                amount: result.amount,
                percent: result.percent,
                label: label || result.label || '',
            },
        }));
        setTimeout(() => tg.close(), 400);
    } catch (e) {
        console.error('sendData failed:', e);
    }
}

async function checkSpinEligibility() {
    if (!USER_ID) {
        showMsg('تعذر تحديد المستخدم');
        startButton.classList.add('disabled');
        return;
    }

    if (IS_TELEGRAM_WEBAPP) {
        document.getElementById('has_free_spin').value = 'True';
        document.getElementById('clock').style.display = 'none';
        updateButtonState();
        return;
    }

    try {
        const res = await fetch(API_BASE + '/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: USER_ID })
        });
        const data = await res.json();

        if (data.allowed) {
            document.getElementById('has_free_spin').value = 'True';
            document.getElementById('clock').style.display = 'none';
        } else {
            document.getElementById('has_free_spin').value = 'False';
            document.getElementById('clock').textContent = data.message || 'يجب أن تشحن اليوم للحصول على تدويرة مجانية';
            document.getElementById('clock').style.display = 'block';
        }
        updateButtonState();
    } catch (e) {
        showMsg('خطأ في الاتصال بالسيرفر');
        startButton.classList.add('disabled');
    }
}

// ── الاحتفال ──
function shouldCelebrate(chance) {
    const matchedSegment = (wheelSegments || []).find(item => item.code === chance);
    if (!matchedSegment) return false;
    return Boolean(matchedSegment.celebrate);
}

function shouldFireworks(chance) {
    const matchedSegment = (wheelSegments || []).find(item => item.code === chance);
    if (!matchedSegment) return false;
    return Boolean(matchedSegment.fireworks);
}

function startCelebration(chance, doConfetti, doFireworks) {
    if (doConfetti) {
        confetti({
            particleCount: 150,
            spread: 70,
            origin: { y: 0.6 },
            colors: ['#ffd700', '#ff6b35', '#ff8c42', '#2dd4bf', '#f472b6']
        });
    }
}

// ── الدوران ──
function getFrontendSegmentDegree(segmentIndex) {
    if (!wheelSegments.length) return 0;
    const anglePerSegment = 360 / wheelSegments.length;
    const centerAngle = (segmentIndex * anglePerSegment) + (anglePerSegment / 2);
    return Math.round(360 - centerAngle);
}

function buildSpinPayload() {
    const activeSegments = Array.isArray(wheelSegments) ? wheelSegments : [];
    if (!activeSegments.length) return null;

    const selectedIndex = Math.floor(Math.random() * activeSegments.length);
    const selectedSegment = activeSegments[selectedIndex] || {};
    const selectedLabel = String(selectedSegment.label || 'قطاع بدون اسم').trim() || 'قطاع بدون اسم';
    const reward_type = String(selectedSegment.reward_type || selectedSegment.type || 'none');
    const result = { type: reward_type };

    if (reward_type === 'cash') {
        result.amount = Number(selectedSegment.amount ?? selectedSegment.value ?? 0);
    } else if (reward_type === 'bonus') {
        result.percent = Number(selectedSegment.percent ?? selectedSegment.value ?? 0);
    } else if (reward_type === 'gift') {
        result.label = selectedLabel;
    }

    return {
        status: "1",
        degree: getFrontendSegmentDegree(selectedIndex),
        win: 0,
        win_type: 0,
        chance: selectedSegment.code || `segment_${selectedIndex}`,
        reward_type,
        cad_text: selectedLabel,
        result
    };
}

function buildTrialSpinPayload() {
    const activeSegments = Array.isArray(wheelSegments) ? wheelSegments : [];
    if (!activeSegments.length) return null;
    const selectedIndex = Math.floor(Math.random() * activeSegments.length);
    const selectedSegment = activeSegments[selectedIndex] || {};
    const selectedLabel = String(selectedSegment.label || 'قطاع بدون اسم').trim() || 'قطاع بدون اسم';
    return {
        status: "1",
        degree: getFrontendSegmentDegree(selectedIndex),
        win: 0,
        win_type: 0,
        chance: selectedSegment.code || '',
        reward_type: 'trial',
        cad_text: `لفة تجريبية فقط\nالنتيجة: ${selectedLabel}\nهذه التجربة لا تمثل لعباً حقيقياً ولا تصرف أي جائزة.`
    };
}

function startTrialSpin() {
    if (!isTrialSpinEnabled() || isWheelSpinning) return;
    const payload = buildTrialSpinPayload();
    if (!payload) {
        showWheelStoppedMessage('لا توجد قطاعات متاحة لتجربة العجلة', 'error');
        return;
    }

    isTrialSpinActive = true;
    startButton.classList.remove('attention');
    startButton.style.pointerEvents = 'none';
    startButton.classList.add('disabled');
    isWheelSpinning = true;
    pendingWheelResize = false;
    updateTrialSpinPanelVisibility(true);
    document.getElementById('clock').style.display = 'none';

    // إمالة العجلة وبدء كرة الروليت
    tiltWheel();

    if (resultBox) {
        resultBox.style.display = 'none';
        resultBox.className = '';
    }
    startButton.classList.remove('respin-active');

    landingDeg = normalizeRotationDegrees(payload.degree);
    deg = buildVisualSpinTarget(payload.degree);
    winned = parseInt(payload.win);
    win_type = parseInt(payload.win_type);
    cad_text = payload.cad_text;
    chance = payload.chance;
    rewardType = String(payload.reward_type || '');

    const spinDurationMs = 12000;

    // تعيين هدف الكرة
    const r3dIdx = (wheelSegments || []).findIndex(function(s){ return s.code === payload.chance; });
    setBallResult(r3dIdx >= 0 ? r3dIdx : 0, spinDurationMs);

    wheel.style.transition = `transform ${spinDurationMs}ms cubic-bezier(0.16, 1, 0.3, 1)`;
    applyWheelRotation(deg);
    wheel.classList.add('blur');
}

// ── حدث النقر على الزر الرئيسي ──
startButton.addEventListener('click', () => {
    const has_free_spin = document.getElementById('has_free_spin').value;
    if (has_free_spin === 'False') return;

    const payload = buildSpinPayload();
    if (!payload) {
        showWheelStoppedMessage('لا توجد قطاعات متاحة لتدوير العجلة', 'error');
        return;
    }

    startButton.classList.remove('attention');
    startButton.style.pointerEvents = 'none';
    startButton.classList.add('disabled');
    isWheelSpinning = true;
    pendingWheelResize = false;
    updateTrialSpinPanelVisibility(true);
    document.getElementById('clock').style.display = 'none';

    // إمالة العجلة
    tiltWheel();

    if (resultBox) {
        resultBox.style.display = 'none';
        resultBox.className = '';
    }
    startButton.classList.remove('respin-active');

    const runSpinAnimation = () => {
        landingDeg = normalizeRotationDegrees(payload.degree);
        deg = buildVisualSpinTarget(payload.degree);
        winned = parseInt(payload.win);
        win_type = parseInt(payload.win_type);
        cad_text = payload.cad_text;
        chance = payload.chance;
        rewardType = String(payload.reward_type || '');
        pendingSpinPayload = payload;

        const spinDurationMs = 12000;
        const r3dIdx = (wheelSegments || []).findIndex(function(s){ return s.code === payload.chance; });
        setBallResult(r3dIdx >= 0 ? r3dIdx : 0, spinDurationMs);

        wheel.style.transition = `transform ${spinDurationMs}ms cubic-bezier(0.16, 1, 0.3, 1)`;
        applyWheelRotation(deg);
        wheel.classList.add('blur');
    };

    if (IS_TELEGRAM_WEBAPP) {
        runSpinAnimation();
        return;
    }

    fetch(API_BASE + '/spin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: USER_ID, result: payload.result })
    })
    .then(res => res.json())
    .then(json => {
        if (!json.success) {
            isWheelSpinning = false;
            untiltWheel();
            startButton.style.pointerEvents = 'auto';
            startButton.classList.remove('disabled');
            document.getElementById('clock').style.display = 'block';
            updateTrialSpinPanelVisibility(false);
            showWheelStoppedMessage('⏹️ ' + (json.message || 'فشل تنفيذ الدوران'));
            return;
        }
        runSpinAnimation();
    })
    .catch(error => {
        console.error('خطأ في الطلب:', error);
        isWheelSpinning = false;
        untiltWheel();
        startButton.style.pointerEvents = 'auto';
        startButton.classList.remove('disabled');
        document.getElementById('clock').style.display = 'block';
        updateTrialSpinPanelVisibility(false);
        showWheelStoppedMessage('حدث خطأ في الاتصال، يرجى المحاولة مرة أخرى', 'error');
    });
});

// ── انتهاء الدوران ──
wheel.addEventListener('transitionend', (event) => {
    if (event.target !== wheel || event.propertyName !== 'transform') return;

    isWheelSpinning = false;
    wheel.classList.remove('blur');
    wheel.style.transition = 'none';
    currentWheelRotation = landingDeg;
    applyWheelRotation(currentWheelRotation);

    // إعادة العجلة للوضع الطبيعي بعد ثانية
    setTimeout(() => {
        untiltWheel();
    }, 1000);

    if (pendingWheelResize) {
        scheduleWheelResize(true);
    }

    if (cad_text && cad_text.trim()) {
        showResult();
    }

    if (IS_TELEGRAM_WEBAPP && pendingSpinPayload && !isTrialSpinActive) {
        sendPrizeToTelegramBot(pendingSpinPayload.result, pendingSpinPayload.cad_text);
        pendingSpinPayload = null;
    }

    if (isTrialSpinActive) {
        isTrialSpinActive = false;
        document.getElementById('clock').style.display = 'block';
        updateButtonState();
        updateTrialSpinPanelVisibility(false);
        return;
    }

    if (rewardType === 'respin') {
        document.getElementById('has_free_spin').value = 'True';
        startButton.style.pointerEvents = 'auto';
        startButton.classList.remove('disabled');
    } else {
        document.getElementById('has_free_spin').value = 'False';
        startButton.style.pointerEvents = 'none';
        startButton.classList.add('disabled');
    }

    const _doConfetti = shouldCelebrate(chance);
    const _doFireworks = shouldFireworks(chance);
    if (_doConfetti || _doFireworks) {
        startCelebration(chance, _doConfetti, _doFireworks);
    }

    updateTrialSpinPanelVisibility(false);
});

// ── مستمعات الأحداث ──
trialSpinButton.addEventListener('click', startTrialSpin);

window.addEventListener('DOMContentLoaded', () => {
    startButton.classList.add('attention');
});

window.addEventListener('load', () => {
    loadWheelConfigFromDom();
    drawWheel();
    if (!USER_ID) {
        document.getElementById('clock').style.display = 'block';
        document.getElementById('clock').textContent = 'تعذر تحديد المستخدم';
        startButton.classList.add('disabled');
    } else {
        checkSpinEligibility();
    }
});

window.addEventListener('resize', () => {
    if (wheelResizeFrameId) cancelAnimationFrame(wheelResizeFrameId);
    wheelResizeFrameId = requestAnimationFrame(() => {
        wheelResizeFrameId = null;
        drawWheel();
    });
});

// ── شاشة التحميل ──
(function() {
    const loader = document.getElementById('casino-loader');
    const barFill = document.getElementById('cl-bar-fill');
    const ringFill = document.getElementById('cl-ring-fill');
    const pctEl = document.getElementById('cl-percent');
    if (!loader) return;

    const CIRCUMFERENCE = 276.46;
    const startT = Date.now();
    const MIN_SHOW = 1200;
    let progress = 0;

    function setProgress(p) {
        p = Math.min(p, 100);
        if (p <= progress) return;
        progress = p;
        if (barFill) barFill.style.width = p + '%';
        if (pctEl) pctEl.textContent = p + '%';
        if (ringFill) {
            const offset = CIRCUMFERENCE * (1 - p / 100);
            ringFill.style.strokeDashoffset = offset;
        }
        if (p >= 100) finish();
    }

    function finish() {
        const elapsed = Date.now() - startT;
        const wait = Math.max(0, MIN_SHOW - elapsed);
        setTimeout(() => {
            loader.classList.add('cl-done');
            setTimeout(() => { loader.remove(); }, 950);
        }, wait);
    }

    // محاكاة التحميل
    let loadProgress = 0;
    const loadInterval = setInterval(() => {
        loadProgress += Math.random() * 15 + 5;
        if (loadProgress >= 100) {
            loadProgress = 100;
            clearInterval(loadInterval);
        }
        setProgress(loadProgress);
    }, 200);

    setTimeout(() => setProgress(100), 5000);
})();
