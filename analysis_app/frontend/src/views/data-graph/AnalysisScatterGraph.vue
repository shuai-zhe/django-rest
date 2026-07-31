<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectData } from "@/composables/useProjectData"

const router = useRouter()

// ==================== Props ====================
const props = defineProps({
    rankMin: { type: Number, default: null },
    rankMax: { type: Number, default: null },
    mcMin: { type: Number, default: null },
    mcMax: { type: Number, default: null },
    volMin: { type: Number, default: null },
    volMax: { type: Number, default: null },
    symbols: { type: String, default: '' },
    riseMin: { type: Number, default: null },
    activeTimeFrame: { type: String, default: 'day' },
})

// ==================== 响应式状态 ====================
const canvasRef = ref(null)
const { projectListData, loading, progress, fetchData, startAutoRefresh, stopAutoRefresh } = useProjectData()

// ==================== Canvas 命令式状态（不参与 Vue 响应式） ====================
let animationId = null
let cleanupFns = []
let bubbles = []
let ctx = null
let W = 0, H = 0

// 拖拽 & 选中
let draggedBubble = null
let selectedBubble = null
let dragOffX = 0, dragOffY = 0
let dragTargetX = 0, dragTargetY = 0
let startMX = 0, startMY = 0
let clickHit = null

// 动画帧状态
let lastTime = 0, pulseTime = 0

// ==================== 常量 & 纯函数 ====================
function riseColor(rise) {
    return rise >= 0 ? '#2ecc71' : '#e74c3c'
}

function randomInRange(lo, hi) {
    return lo + Math.random() * (hi - lo)
}

function hexToRGBA(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    return `rgba(${r},${g},${b},${alpha})`
}

function getRiseValue(item, timeFrame) {
    return item?.extra_info?.performance?.[timeFrame] ?? 0
}

// ==================== 工具：自适应文本 & 半径 ====================
function fitFontSize(ctx, text, maxWidth, baseSize, minSize) {
    let size = baseSize
    ctx.font = `bold ${size}px "Microsoft YaHei", sans-serif`
    const w = ctx.measureText(text).width
    if (w > maxWidth) {
        size = Math.max(minSize, size * (maxWidth / w) * 0.92)
        ctx.font = `bold ${size}px "Microsoft YaHei", sans-serif`
    }
    return size
}

function drawClippedText(ctx, text, x, y, maxWidth, baseSize, minSize, color) {
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillStyle = color
    const actualSize = fitFontSize(ctx, text, maxWidth, baseSize, minSize)
    ctx.fillText(text, x, y)
    return actualSize
}

function scaledRadii() {
    // 基于画布短边缩放半径，适配不同设备
    const baseDim = Math.min(W, H)
    const scale = Math.max(0.45, Math.min(baseDim / 750, 1.8))
    // 绝对硬边界：最小不低于 12px，最大不超过画布短边的 20% 且不高于 120px
    const absoluteMax = Math.min(120, baseDim * 0.20)
    const absoluteMin = 12
    return {
        smallMin: Math.max(absoluteMin, 16 * scale),
        smallMax: Math.min(absoluteMax, Math.max(absoluteMin, 28 * scale)),
        largeMin: Math.min(absoluteMax, Math.max(absoluteMin, 36 * scale)),
        largeMax: Math.min(absoluteMax, Math.max(absoluteMin, 90 * scale)),
        threshold: 5,
    }
}

// ==================== 画布尺寸（100% 填充） ====================
function resizeCanvas() {
    const canvas = canvasRef.value
    if (!canvas) return false
    const rect = canvas.getBoundingClientRect()
    const cssW = rect.width
    const cssH = rect.height
    if (cssW === 0 || cssH === 0) return false
    const dpr = window.devicePixelRatio || 1
    canvas.width = cssW * dpr
    canvas.height = cssH * dpr
    ctx = canvas.getContext('2d')
    ctx.scale(dpr, dpr) // 后续所有坐标使用 CSS 像素
    W = cssW
    H = cssH
    return true
}

// ==================== 构建气泡（涨幅等比布局） ====================
function buildBubbles(timeFrame) {
    const items = projectListData.value
    if (!items || items.length === 0) return []

    // 过滤掉涨幅为 0 的项目 + 排名/市值/成交量/symbols/涨幅阈值
    const filtered = items.filter(d => {
        const rise = getRiseValue(d, timeFrame)
        if (rise === 0) return false
        // 涨幅阈值（按绝对值，涨跌都算）
        if (props.riseMin != null && Math.abs(rise) < props.riseMin) return false
        // 排名范围
        const rank = d.extra_info?.rank ?? 999
        if (props.rankMin != null && rank < props.rankMin) return false
        if (props.rankMax != null && rank > props.rankMax) return false
        // 市值范围
        const mc = d.market_cap_dict?.spot ?? 0
        if (props.mcMin != null && mc < props.mcMin) return false
        if (props.mcMax != null && mc > props.mcMax) return false
        // 成交量范围
        const vol = d.volume_dict?.spot ?? 0
        if (props.volMin != null && vol < props.volMin) return false
        if (props.volMax != null && vol > props.volMax) return false
        // 交易所过滤（extra_info.symbols 中是否有选中的交易所）
        if (props.symbols) {
            const syms = d.extra_info?.symbols
            if (!syms || !syms[props.symbols]) return false
        }
        return true
    })
    if (filtered.length === 0) return []

    const padding = 12

    // 提取涨幅数据
    const raw = filtered.map(d => ({
        name: d.display_name || d.name,
        code_id: d.code_id,
        rise: getRiseValue(d, timeFrame),
        color: riseColor(getRiseValue(d, timeFrame)),
    }))

    // 打乱顺序（不要排序，随机散布更有爆发感）
    for (let i = raw.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [raw[i], raw[j]] = [raw[j], raw[i]]
    }

    // === 正方形面积等比布局：每个气泡分到面积 ∝ |rise| ===
    const usableW = W - padding * 2
    const usableH = H - padding * 2
    const totalArea = usableW * usableH
    const totalAbs = raw.reduce((s, b) => s + Math.abs(b.rise), 0)
    const gap = 4

    // 1) 先算原始占比
    const withShare = raw.map(b => ({
        ...b,
        share: totalAbs > 0 ? Math.abs(b.rise) / totalAbs : 1 / raw.length,
    }))

    // 2) 异常值封顶：单个体积最多占屏幕 15%，超出的释放出来
    const MAX_SHARE = 0.15
    let surplus = 0
    for (const b of withShare) {
        if (b.share > MAX_SHARE) {
            surplus += b.share - MAX_SHARE
            b.share = MAX_SHARE
        }
    }

    // 3) 释放的空间按比例分给未封顶的项目
    if (surplus > 0) {
        const normalTotal = withShare.reduce((s, b) => s + (b.share < MAX_SHARE ? b.share : 0), 0)
        if (normalTotal > 0) {
            for (const b of withShare) {
                if (b.share < MAX_SHARE) {
                    b.share += surplus * (b.share / normalTotal)
                }
            }
        }
    }

    // 4) 用调整后的 share 计算边长 & 半径
    const withCell = withShare.map(b => {
        const cellSize = Math.sqrt(b.share * totalArea)
        const r = Math.max(5, cellSize / 2 - gap)
        return { ...b, r, cellSize }
    })

    // 流式布局：左→右，上→下
    const result = []
    let cursorX = padding
    let cursorY = padding
    let rowMaxH = 0

    for (const b of withCell) {
        // 换行处理
        if (cursorX + b.cellSize > padding + usableW) {
            cursorX = padding
            cursorY += rowMaxH
            rowMaxH = 0
        }
        // 防超出底部
        if (cursorY + b.cellSize > padding + usableH) {
            cursorY = padding + usableH - b.cellSize
        }

        const x = Math.max(b.r + 2, Math.min(W - b.r - 2, cursorX + b.cellSize / 2))
        const y = Math.max(b.r + 2, Math.min(H - b.r - 2, cursorY + b.cellSize / 2))

        result.push({
            name: b.name,
            code_id: b.code_id,
            rise: b.rise,
            r: b.r,
            x, y,
            vx: randomInRange(-0.2, 0.2),
            vy: randomInRange(-0.2, 0.2),
            color: b.color,
            glowPhase: Math.random() * Math.PI * 2,
        })

        cursorX += b.cellSize
        rowMaxH = Math.max(rowMaxH, b.cellSize)
    }
    return result
}

// ==================== 切换时间维度 ====================
function switchTimeFrame(key) {
    // 已由 prop watch 代理
}

// 时间维度变化→重建气泡
watch(() => props.activeTimeFrame, (key) => {
    if (projectListData.value.length === 0) return
    bubbles = buildBubbles(key)
    selectedBubble = null
    draggedBubble = null
})

// ==================== 碰撞检测 ====================
function resolveBubbleCollision(a, b) {
    const dx = b.x - a.x
    const dy = b.y - a.y
    const dist = Math.sqrt(dx * dx + dy * dy)
    const minDist = a.r + b.r + 4 // 间距从 2 → 4，减少粘连
    if (dist < minDist && dist > 0) {
        const overlap = (minDist - dist) / 2
        const nx = dx / dist
        const ny = dy / dist
        const step = 0.45 // 从 0.15 → 0.45，每帧推开更多
        a.x -= nx * overlap * step
        a.y -= ny * overlap * step
        b.x += nx * overlap * step
        b.y += ny * overlap * step

        const dvx = a.vx - b.vx
        const dvy = a.vy - b.vy
        const dot = dvx * nx + dvy * ny
        if (dot > 0) {
            const damp = 0.50 // 从 0.25 → 0.50，速度交换更足
            a.vx -= dot * nx * damp
            a.vy -= dot * ny * damp
            b.vx += dot * nx * damp
            b.vy += dot * ny * damp
        }
    }
}

// ==================== 事件处理 ====================
function handleMouseDown(e) {
    const rect = canvasRef.value.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    startMX = mx
    startMY = my
    dragTargetX = mx // 重置，防止 mouseup 时用旧值算距离
    dragTargetY = my
    clickHit = null

    for (let i = bubbles.length - 1; i >= 0; i--) {
        const b = bubbles[i]
        const dx = mx - b.x
        const dy = my - b.y
        if (dx * dx + dy * dy <= b.r * b.r) {
            selectedBubble = null // 拖拽新球时取消之前的选中
            clickHit = b
            draggedBubble = b
            dragOffX = mx - b.x
            dragOffY = my - b.y
            dragTargetX = mx - dragOffX
            dragTargetY = my - dragOffY
            break
        }
    }
}

function handleMouseMove(e) {
    if (!draggedBubble) return
    const rect = canvasRef.value.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top

    dragTargetX = mx - dragOffX
    dragTargetY = my - dragOffY

    const b = draggedBubble
    if (dragTargetX - b.r < 0) dragTargetX = b.r
    if (dragTargetX + b.r > W) dragTargetX = W - b.r
    if (dragTargetY - b.r < 0) dragTargetY = b.r
    if (dragTargetY + b.r > H) dragTargetY = H - b.r
}

function handleMouseUp(e) {
    if (clickHit) {
        // 用 mouseup 时的实际鼠标位置判断是否拖拽
        const rect = canvasRef.value.getBoundingClientRect()
        const mx = e.clientX - rect.left
        const my = e.clientY - rect.top
        const dist = Math.hypot(mx - startMX, my - startMY)
        if (dist < 5) {
            // 点击气泡 → 跳转项目详情页
            selectedBubble = clickHit
            const codeId = clickHit?.code_id
            if (codeId) router.push(`/project/${codeId}`)
        }
    } else {
        selectedBubble = null
    }
    draggedBubble = null
    clickHit = null
}

function handleMouseLeave() {
    draggedBubble = null
}

// ==================== 数据变化→重建气泡（初次加载 + 定时刷新） ====================
watch(projectListData, () => {
    if (projectListData.value.length > 0) {
        bubbles = buildBubbles(props.activeTimeFrame)
        selectedBubble = null
        draggedBubble = null
    }
})

// 任何筛选条件变化→重建气泡
watch(
    () => [props.rankMin, props.rankMax, props.mcMin, props.mcMax, props.volMin, props.volMax, props.symbols, props.riseMin],
    () => {
        if (projectListData.value.length > 0) {
            bubbles = buildBubbles(props.activeTimeFrame)
            selectedBubble = null
            draggedBubble = null
        }
    }
)

// ==================== 动画帧 ====================
function frame(now) {
    if (!ctx) {
        animationId = requestAnimationFrame(frame)
        return
    }

    const dt = Math.min((now - lastTime) / 16.67, 3)
    lastTime = now
    pulseTime += dt * 0.04

    // 清屏
    ctx.fillStyle = '#0f1923'
    ctx.fillRect(0, 0, W, H)

    // 更新位置
    for (const b of bubbles) {
        if (b === draggedBubble) {
            b.x += (dragTargetX - b.x) * 0.08 * dt
            b.y += (dragTargetY - b.y) * 0.08 * dt
        } else {
            b.x += b.vx * dt
            b.y += b.vy * dt
        }

        if (b.x - b.r < 0) { b.x = b.r; b.vx = Math.abs(b.vx) }
        if (b.x + b.r > W) { b.x = W - b.r; b.vx = -Math.abs(b.vx) }
        if (b.y - b.r < 0) { b.y = b.r; b.vy = Math.abs(b.vy) }
        if (b.y + b.r > H) { b.y = H - b.r; b.vy = -Math.abs(b.vy) }
    }

    // 气泡间碰撞
    for (let i = 0; i < bubbles.length; i++) {
        for (let j = i + 1; j < bubbles.length; j++) {
            resolveBubbleCollision(bubbles[i], bubbles[j])
        }
    }

    // 绘制
    for (const b of bubbles) {
        b.glowPhase += 0.02 * dt

        // 外层光晕
        const glowGrad = ctx.createRadialGradient(b.x, b.y, b.r * 0.2, b.x, b.y, b.r * 1.35)
        glowGrad.addColorStop(0, hexToRGBA(b.color, 0.35))
        glowGrad.addColorStop(1, hexToRGBA(b.color, 0))
        ctx.beginPath()
        ctx.arc(b.x, b.y, b.r * 1.35, 0, Math.PI * 2)
        ctx.fillStyle = glowGrad
        ctx.fill()

        // 选中高亮
        const isSel = b === draggedBubble || b === selectedBubble
        let selGlow = 0
        if (isSel) {
            selGlow = 0.45 + 0.35 * Math.sin(pulseTime * 1.5)
            ctx.beginPath()
            ctx.arc(b.x, b.y, b.r + 2, 0, Math.PI * 2)
            ctx.strokeStyle = `rgba(255,255,255,${selGlow * 0.7})`
            ctx.lineWidth = 4
            ctx.stroke()
        }

        // 主体
        ctx.beginPath()
        ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2)

        // 外轮廓阴影
        const shadow = ctx.createRadialGradient(
            b.x + b.r * 0.25, b.y + b.r * 0.25, 0,
            b.x, b.y, b.r
        )
        shadow.addColorStop(0, 'rgba(0,0,0,0)')
        shadow.addColorStop(0.7, 'rgba(0,0,0,0)')
        shadow.addColorStop(0.95, 'rgba(0,0,0,0.12)')
        shadow.addColorStop(1, 'rgba(0,0,0,0.25)')
        ctx.fillStyle = shadow
        ctx.fill()

        // 主体渐变
        const lx = b.x - b.r * 0.35
        const ly = b.y - b.r * 0.35
        const body = ctx.createRadialGradient(lx, ly, 0, b.x, b.y, b.r)
        const baseAlpha = isSel ? 0.55 : 0.40
        body.addColorStop(0, hexToRGBA(b.color, baseAlpha * 0.9))
        body.addColorStop(0.3, hexToRGBA(b.color, baseAlpha * 0.65))
        body.addColorStop(0.7, hexToRGBA(b.color, baseAlpha * 0.4))
        body.addColorStop(1, hexToRGBA(b.color, baseAlpha * 0.15))
        ctx.fillStyle = body
        ctx.fill()

        // 描边 — 加宽 + 向内渐变（从边缘向内渐隐）
        const borderW = Math.max(2.5, Math.min(b.r * 0.08, 7))
        const borderGrad = ctx.createRadialGradient(
            b.x, b.y, b.r - borderW,
            b.x, b.y, b.r
        )
        borderGrad.addColorStop(0, hexToRGBA(b.color, 0))
        borderGrad.addColorStop(0.6, hexToRGBA(b.color, 0.08))
        borderGrad.addColorStop(1, hexToRGBA(b.color, 0.55))
        ctx.beginPath()
        ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2)
        ctx.fillStyle = borderGrad
        ctx.fill()

        // 高光
        ctx.beginPath()
        ctx.ellipse(b.x - b.r * 0.25, b.y - b.r * 0.25, b.r * 0.08, b.r * 0.05, -0.5, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(255,255,255,${isSel ? 0.3 : 0.18})`
        ctx.fill()

        // ==== 文字（裁剪到球内，防止溢出） ====
        ctx.save()
        ctx.beginPath()
        ctx.arc(b.x, b.y, b.r - 3, 0, Math.PI * 2)
        ctx.clip()

        // 名称
        const nameMaxW = (b.r - 3) * 2
        drawClippedText(ctx, b.name, b.x, b.y - b.r * 0.18,
            nameMaxW, Math.max(10, b.r * 0.30), 7, '#ffffff')

        // 涨幅
        const prefix = b.rise >= 0 ? '+' : ''
        const riseText = `${prefix}${b.rise.toFixed(1)}%`
        drawClippedText(ctx, riseText, b.x, b.y + b.r * 0.22,
            nameMaxW, Math.max(9, b.r * 0.26), 7, '#ffd93d')

        ctx.restore()
    }

    animationId = requestAnimationFrame(frame)
}

// ==================== 生命周期 ====================
onMounted(() => {
    const canvas = canvasRef.value
    if (!canvas) return
    if (!resizeCanvas()) return

    // 注册事件
    canvas.addEventListener('mousedown', handleMouseDown)
    canvas.addEventListener('mousemove', handleMouseMove)
    canvas.addEventListener('mouseup', handleMouseUp)
    canvas.addEventListener('mouseleave', handleMouseLeave)
    cleanupFns.push(() => {
        canvas.removeEventListener('mousedown', handleMouseDown)
        canvas.removeEventListener('mousemove', handleMouseMove)
        canvas.removeEventListener('mouseup', handleMouseUp)
        canvas.removeEventListener('mouseleave', handleMouseLeave)
    })

    // 窗口 resize → 重设画布 + 按比例缩放已有气泡位置
    const handleResize = () => {
        const oldW = W
        const oldH = H
        if (!resizeCanvas()) return
        if (bubbles.length > 0 && oldW > 0 && oldH > 0) {
            const sx = W / oldW
            const sy = H / oldH
            for (const b of bubbles) {
                b.x *= sx
                b.y *= sy
                b.vx *= sx
                b.vy *= sy
            }
        }
    }
    window.addEventListener('resize', handleResize)
    cleanupFns.push(() => window.removeEventListener('resize', handleResize))

    // ResizeObserver：画布尺寸变化（含返回本页布局定型）后，按新尺寸重建气泡，
    // 避免用极小尺寸生成气泡后无法修正
    const buildAtCurrentSize = () => {
        if (projectListData.value.length > 0) {
            bubbles = buildBubbles(props.activeTimeFrame)
            selectedBubble = null
            draggedBubble = null
        }
    }
    let resizeObserver = null
    if (typeof ResizeObserver !== 'undefined') {
        resizeObserver = new ResizeObserver(() => {
            if (!resizeCanvas()) return
            buildAtCurrentSize()
        })
        resizeObserver.observe(canvas)
        cleanupFns.push(() => resizeObserver.disconnect())
    }

    // 启动空帧循环（等待数据到达后真正开始绘制）
    animationId = requestAnimationFrame(frame)

    // 数据已缓存（返回本页时 watch 不会重新触发）→ 立即按当前尺寸重建气泡
    if (projectListData.value.length > 0) {
        buildAtCurrentSize()
    }

    // 拉取项目数据（共享，只会请求一次），就绪后启动 60s 定时刷新
    fetchData().then(() => {
        buildAtCurrentSize()
        startAutoRefresh(60000)
    })
})

onUnmounted(() => {
    stopAutoRefresh()
    if (animationId) {
        cancelAnimationFrame(animationId)
        animationId = null
    }
    cleanupFns.forEach(fn => fn())
    cleanupFns = []
})
</script>

<template>
    <div class="bubble-chart-container">
        <!-- Canvas 区域 -->
        <div class="canvas-wrapper">
            <canvas ref="canvasRef" id="bubbleCanvas"></canvas>
            <div v-if="loading && projectListData.length === 0" class="loading-overlay">
                <div class="loading-spinner"></div>
                <span>加载数据中...</span>
            </div>
            <div v-else-if="projectListData.length === 0" class="loading-overlay">
                <span>暂无项目数据</span>
            </div>
        </div>
    </div>
</template>

<style scoped>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

.bubble-chart-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
    height: 100vh;
    background: #0f1923;
    font-family: 'Microsoft YaHei', sans-serif;
    padding: 52px 0 0;
    overflow: hidden;
}

/* ---------- Canvas 包裹器 ---------- */
.canvas-wrapper {
    flex: 1;
    min-height: 0;
    width: 100%;
    position: relative;
    border-radius: 8px;
    overflow: hidden;
}

#bubbleCanvas {
    width: 100%;
    height: 100%;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    box-shadow: 0 0 30px rgba(0, 150, 255, 0.15);
    display: block;
}

/* ---------- 加载遮罩 ---------- */
.loading-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 12px;
    background: rgba(15, 25, 35, 0.85);
    color: #8ba4be;
    font-size: 14px;
    border-radius: 8px;
}

.loading-spinner {
    width: 32px;
    height: 32px;
    border: 3px solid #1e3a5f;
    border-top-color: #3b82c4;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}
</style>
