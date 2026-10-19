"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  Layers,
  Palette,
  Sparkles,
  CheckCircle2,
  TrendingUp,
  Sliders,
  MousePointer,
  Square,
  Pipette,
  Code2,
  Maximize2,
  Copy,
  Check,
  Zap,
} from "lucide-react";

export function DarkStudioMockup() {
  const [specularLight, setSpecularLight] = useState(82);
  const [hapticDepth, setHapticDepth] = useState(14);
  const [activeTool, setActiveTool] = useState<"select" | "frame" | "color" | "code">("select");
  const [isRendering, setIsRendering] = useState(false);
  const [renderedCount, setRenderedCount] = useState(482);
  const [copiedHex, setCopiedHex] = useState<string | null>(null);

  const swatches = [
    { hex: "#00F2FE", name: "Cyan", label: "Acento Primario" },
    { hex: "#A78BFA", name: "Lilac", label: "Acento Secundario" },
    { hex: "#34D399", name: "Mint", label: "Estado 60 FPS" },
    { hex: "#F43F5E", name: "Coral", label: "Alerta & Tráfico" },
    { hex: "#111318", name: "Void", label: "Superficie OLED" },
  ];

  const handleCopySwatch = (hex: string) => {
    navigator.clipboard.writeText(hex);
    setCopiedHex(hex);
    setTimeout(() => setCopiedHex(null), 1500);
  };

  const handleRender = () => {
    setIsRendering(true);
    setTimeout(() => {
      setIsRendering(false);
      setRenderedCount((prev) => prev + 1);
    }, 700);
  };

  return (
    <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 mb-24" id="estudio">
      {/* Outer Window Frame */}
      <div className="rounded-2xl sm:rounded-3xl border border-white/10 bg-[#0C0E13]/90 backdrop-blur-2xl shadow-[0_25px_60px_-15px_rgba(0,0,0,0.9)] overflow-hidden">
        {/* Window Titlebar */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3.5 bg-[#151A28]/70 border-b border-white/8">
          {/* Traffic lights & canvas title */}
          <div className="flex items-center gap-2.5">
            <span className="w-3 h-3 rounded-full bg-[#F43F5E] shadow-[0_0_6px_rgba(244,63,94,0.6)]" />
            <span className="w-3 h-3 rounded-full bg-[#FBBF24] shadow-[0_0_6px_rgba(251,191,36,0.6)]" />
            <span className="w-3 h-3 rounded-full bg-[#34D399] shadow-[0_0_6px_rgba(52,211,153,0.6)]" />
            <span className="ml-3 font-mono text-xs text-[#94A3B8] truncate max-w-[210px] sm:max-w-none">
              Serena Studio — Neo-Design System 2026.canvas
            </span>
          </div>

          {/* Right Status Indicator */}
          <div className="flex items-center gap-3">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[#34D399]/10 border border-[#34D399]/30 text-[#34D399] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#34D399] animate-pulse" />
              88% Compilado
            </span>
            <div className="hidden sm:flex items-center gap-2 text-[#94A3B8]">
              <Maximize2 className="w-4 h-4 hover:text-white cursor-pointer transition-colors" />
            </div>
          </div>
        </div>

        {/* Studio Workspace 3-Column Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[520px]">
          {/* Left Column: Component Tree & Token Swatches (3 cols) */}
          <div className="lg:col-span-3 border-b lg:border-b-0 lg:border-r border-white/8 bg-[#0F121C]/60 p-4 sm:p-5 flex flex-col justify-between">
            <div className="space-y-5">
              <div className="flex items-center justify-between text-[#94A3B8]">
                <span className="text-[11px] font-bold tracking-wider uppercase">
                  Árbol de Componentes
                </span>
                <span className="text-xs font-mono text-[#00F2FE] bg-[#00F2FE]/10 px-2 py-0.5 rounded">
                  v3.2
                </span>
              </div>

              {/* Hierarchy Nodes */}
              <div className="space-y-1.5">
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#1E1F25] text-[#F8FAFC] border-l-2 border-[#00F2FE]">
                  <Layers className="w-4 h-4 text-[#00F2FE]" />
                  <span className="text-xs font-semibold">Componentes Activos</span>
                </div>

                <div className="pl-6 space-y-1 text-xs">
                  <div className="flex items-center justify-between px-2.5 py-1.5 rounded-md text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-white/5 cursor-pointer transition-colors">
                    <span className="truncate">ModalDarkSurface.tsx</span>
                    <span className="w-1.5 h-1.5 rounded-full bg-[#00F2FE] shadow-[0_0_6px_#00F2FE]" />
                  </div>
                  <div className="flex items-center justify-between px-2.5 py-1.5 rounded-md text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-white/5 cursor-pointer transition-colors">
                    <span className="truncate">NeonHaloButton.css</span>
                    <span className="w-1.5 h-1.5 rounded-full bg-[#A78BFA] shadow-[0_0_6px_#A78BFA]" />
                  </div>
                  <div className="flex items-center justify-between px-2.5 py-1.5 rounded-md text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-white/5 cursor-pointer transition-colors">
                    <span className="truncate">QuantumCard.tsx</span>
                    <span className="w-1.5 h-1.5 rounded-full bg-[#34D399] shadow-[0_0_6px_#34D399]" />
                  </div>
                </div>

                <div className="flex items-center gap-2 px-3 py-2 rounded-lg text-[#94A3B8] hover:text-white hover:bg-white/5 cursor-pointer transition-colors mt-2">
                  <Palette className="w-4 h-4 text-[#A78BFA]" />
                  <span className="text-xs font-medium">Paletas de Tokens</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg text-[#94A3B8] hover:text-white hover:bg-white/5 cursor-pointer transition-colors">
                  <Sparkles className="w-4 h-4 text-[#34D399]" />
                  <span className="text-xs font-medium">Micro-animaciones</span>
                </div>
              </div>
            </div>

            {/* Token Swatches Row */}
            <div className="pt-4 border-t border-white/8 mt-4">
              <div className="flex items-center justify-between mb-2.5">
                <span className="text-[11px] font-bold tracking-wider uppercase text-[#94A3B8]">
                  Paleta Serena OLED
                </span>
                {copiedHex && (
                  <span className="text-[10px] text-[#34D399] font-mono animate-fade-in">
                    ¡Copiado!
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {swatches.map((s) => (
                  <button
                    key={s.hex}
                    onClick={() => handleCopySwatch(s.hex)}
                    className="w-7 h-7 rounded-lg border border-white/20 transition-transform hover:scale-110 active:scale-95 relative group cursor-pointer"
                    style={{
                      backgroundColor: s.hex,
                      boxShadow: `0 0 10px ${s.hex}40`,
                    }}
                    title={`${s.name}: ${s.hex} (Click para copiar)`}
                  >
                    <span className="absolute -top-7 left-1/2 -translate-x-1/2 px-1.5 py-0.5 rounded bg-black/90 text-[10px] font-mono text-white opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-20">
                      {s.hex}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Center Column: Live Interactive Canvas (6 cols) */}
          <div className="lg:col-span-6 p-6 sm:p-8 flex flex-col items-center justify-center relative bg-[#090B10]/95 overflow-hidden">
            {/* Subtle Vignette Glow */}
            <div
              className="absolute inset-0 pointer-events-none transition-opacity duration-300"
              style={{
                background: `radial-gradient(circle at center, rgba(0, 242, 254, ${
                  specularLight * 0.0012
                }) 0, rgba(167, 139, 250, ${specularLight * 0.0006}) 40%, transparent 75%)`,
              }}
            />

            {/* Interactive Quantum Card in Studio */}
            <div
              className="w-full max-w-sm rounded-2xl p-5 sm:p-6 bg-[#161B2B]/80 border transition-all duration-200 backdrop-blur-xl relative z-10"
              style={{
                borderColor: `rgba(255, 255, 255, ${0.08 + specularLight * 0.0015})`,
                boxShadow: `0 20px 50px -10px rgba(0,0,0,0.8), 0 0 ${specularLight * 0.4}px rgba(0, 242, 254, ${
                  specularLight * 0.003
                })`,
                transform: `translateY(-${hapticDepth * 0.25}px)`,
              }}
            >
              {/* Card Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-[#1E2438] flex items-center justify-center border border-white/10">
                    <Zap className="w-4 h-4 text-[#00F2FE]" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-[#F8FAFC]">Quantum Card</h4>
                    <p className="text-[11px] text-[#94A3B8]">Shader Mesh v3.1</p>
                  </div>
                </div>
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#00F2FE]/10 border border-[#00F2FE]/30 text-[#00F2FE]">
                  60 FPS
                </span>
              </div>

              {/* Reactive Live Sliders */}
              <div className="space-y-4 mb-5">
                <div>
                  <div className="flex justify-between text-xs font-medium text-[#94A3B8] mb-1.5">
                    <span>Luminosidad Especular</span>
                    <span className="text-[#00F2FE] font-mono font-semibold">
                      {specularLight}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="20"
                    max="100"
                    value={specularLight}
                    onChange={(e) => setSpecularLight(Number(e.target.value))}
                    className="w-full h-1.5 bg-[#1E2438] rounded-full appearance-none cursor-pointer accent-[#00F2FE]"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-xs font-medium text-[#94A3B8] mb-1.5">
                    <span>Profundidad Háptica (Z-Index)</span>
                    <span className="text-[#A78BFA] font-mono font-semibold">
                      {hapticDepth}px
                    </span>
                  </div>
                  <input
                    type="range"
                    min="4"
                    max="30"
                    value={hapticDepth}
                    onChange={(e) => setHapticDepth(Number(e.target.value))}
                    className="w-full h-1.5 bg-[#1E2438] rounded-full appearance-none cursor-pointer accent-[#A78BFA]"
                  />
                </div>
              </div>

              {/* Card Actions */}
              <div className="flex items-center justify-between pt-3.5 border-t border-white/8">
                <div className="flex items-center gap-2 text-xs text-[#34D399]">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span className="text-[11px] text-[#94A3B8]">Sin halo blooming</span>
                </div>
                <button
                  onClick={handleRender}
                  disabled={isRendering}
                  className="px-3.5 py-1.5 rounded-lg bg-[#00F2FE]/15 hover:bg-[#00F2FE] hover:text-[#090B10] border border-[#00F2FE]/40 text-[#00F2FE] text-xs font-bold transition-all active:scale-95 cursor-pointer flex items-center gap-1.5"
                >
                  {isRendering ? (
                    <>
                      <span className="w-2.5 h-2.5 rounded-full border-2 border-current border-t-transparent animate-spin" />
                      <span>Renderizando...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3 h-3" />
                      <span>Renderizar ({renderedCount})</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Floating Quick Tools Dock */}
            <div className="mt-7 flex items-center gap-1 sm:gap-2 px-3 py-1.5 rounded-full bg-[#151A28]/90 border border-white/12 shadow-2xl backdrop-blur-xl z-10">
              <button
                onClick={() => setActiveTool("select")}
                className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                  activeTool === "select"
                    ? "bg-[#00F2FE]/20 text-[#00F2FE]"
                    : "text-[#94A3B8] hover:text-white"
                }`}
                title="Puntero Seleccionar"
              >
                <MousePointer className="w-4 h-4" />
              </button>
              <button
                onClick={() => setActiveTool("frame")}
                className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                  activeTool === "frame"
                    ? "bg-[#00F2FE]/20 text-[#00F2FE]"
                    : "text-[#94A3B8] hover:text-white"
                }`}
                title="Diseño de Marco"
              >
                <Square className="w-4 h-4" />
              </button>
              <button
                onClick={() => setActiveTool("color")}
                className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                  activeTool === "color"
                    ? "bg-[#00F2FE]/20 text-[#00F2FE]"
                    : "text-[#94A3B8] hover:text-white"
                }`}
                title="Inspector de Color"
              >
                <Pipette className="w-4 h-4" />
              </button>
              <button
                onClick={() => setActiveTool("code")}
                className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                  activeTool === "code"
                    ? "bg-[#00F2FE]/20 text-[#00F2FE]"
                    : "text-[#94A3B8] hover:text-white"
                }`}
                title="Modo Código React + Tailwind"
              >
                <Code2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Right Column: Real-time Metrics Inspector (3 cols) */}
          <div className="lg:col-span-3 border-t lg:border-t-0 lg:border-l border-white/8 bg-[#0F121C]/60 p-4 sm:p-5 space-y-4">
            <span className="text-[11px] font-bold tracking-wider uppercase text-[#94A3B8] block">
              Métricas en Vivo
            </span>

            {/* Metric 1: Zero Cognitive Fatigue with Soundwave Equilizer */}
            <div className="p-3.5 rounded-xl bg-[#161B2B]/70 border border-white/8">
              <div className="flex items-center justify-between mb-2.5">
                <span className="text-xs font-semibold text-[#F8FAFC]">
                  Cero fatiga cognitiva
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#34D399]/15 text-[#34D399]">
                  Óptimo
                </span>
              </div>
              <div className="h-9 flex items-end gap-1.5 px-1 bg-[#090B10]/50 rounded-lg py-1">
                <div className="flex-1 bg-[#00F2FE]/50 rounded-t-sm animate-wave-1" />
                <div className="flex-1 bg-[#00F2FE]/70 rounded-t-sm animate-wave-2" />
                <div className="flex-1 bg-[#00F2FE] rounded-t-sm animate-wave-3 shadow-[0_0_8px_#00F2FE]" />
                <div className="flex-1 bg-[#A78BFA] rounded-t-sm animate-wave-4 shadow-[0_0_8px_#A78BFA]" />
                <div className="flex-1 bg-[#00F2FE]/80 rounded-t-sm animate-wave-5" />
                <div className="flex-1 bg-[#00F2FE]/60 rounded-t-sm animate-wave-6" />
              </div>
            </div>

            {/* Metric 2: 60 FPS Fluid Animations */}
            <div className="p-3.5 rounded-xl bg-[#161B2B]/70 border border-white/8">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-[#F8FAFC]">
                  60 FPS Animaciones
                </span>
                <span className="font-mono text-xs text-[#00F2FE] font-bold">
                  16.6ms
                </span>
              </div>
              <div className="w-full bg-[#090B10] h-2 rounded-full overflow-hidden p-0.5">
                <div className="bg-gradient-to-r from-[#00F2FE] via-[#A78BFA] to-[#34D399] h-full rounded-full w-[98%]" />
              </div>
            </div>

            {/* Metric 3: Focus Retention */}
            <div className="p-3.5 rounded-xl bg-[#161B2B]/70 border border-white/8">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-[#94A3B8]">Retención de Enfoque</span>
                <span className="text-sm font-bold text-[#F8FAFC]">99.4%</span>
              </div>
              <div className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-[#34D399]">
                <TrendingUp className="w-3.5 h-3.5" />
                <span>+14.2% este mes</span>
              </div>
            </div>

            {/* Token Inspector */}
            <div className="pt-3 border-t border-white/8">
              <span className="text-[11px] font-bold tracking-wider uppercase text-[#94A3B8] block mb-2">
                Token Inspector
              </span>
              <div className="bg-[#090B10] p-2.5 rounded-lg border border-white/8 font-mono text-[11px] space-y-1.5 text-[#94A3B8]">
                <div className="flex justify-between">
                  <span className="text-[#64748B]">--color-void:</span>
                  <span className="text-[#F8FAFC]">#090B10</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#00F2FE]">--glow-cyan:</span>
                  <span className="text-[#00F2FE]">#00F2FE</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#A78BFA]">--accent-lilac:</span>
                  <span className="text-[#A78BFA]">#A78BFA</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#34D399]">--status-mint:</span>
                  <span className="text-[#34D399]">#34D399</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
