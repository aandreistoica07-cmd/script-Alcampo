"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  Layers,
  Sliders,
  Calendar,
  Clock,
  Sparkles,
  CheckCircle2,
  Zap,
} from "lucide-react";

export function DarkShowcase() {
  const [toggleActive, setToggleActive] = useState(true);
  const [sliderVal, setSliderVal] = useState(75);

  const showcaseCards = [
    {
      id: "card-1",
      title: "Panel de Métricas Serena OLED",
      tag: "Analítica Profunda",
      tagColor: "bg-[#00F2FE]/10 text-[#00F2FE] border-[#00F2FE]/30",
      rotation: "lg:-rotate-2",
      borderGlow: "hover:border-[#00F2FE]/40",
      shadow: "hover:shadow-[0_20px_50px_-10px_rgba(0,242,254,0.25)]",
      content: (
        <div className="space-y-4 text-left">
          <div className="flex items-center justify-between pb-3 border-b border-white/8">
            <div>
              <div className="text-xs text-[#94A3B8]">Tiempo en Enfoque Profundo</div>
              <div className="text-2xl font-black text-[#F8FAFC]">4h 45min</div>
            </div>
            <span className="text-xs font-bold text-[#00F2FE] bg-[#00F2FE]/15 px-2.5 py-1 rounded-full border border-[#00F2FE]/30">
              +18% hoy
            </span>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-xs text-[#94A3B8]">
              <span>Ritmo cardíaco de trabajo</span>
              <span className="font-bold text-[#34D399]">Óptimo</span>
            </div>
            <div className="flex items-end gap-1.5 h-16 pt-2">
              {[40, 65, 55, 80, 70, 95, 85].map((h, i) => (
                <div
                  key={i}
                  className="flex-1 bg-gradient-to-t from-[#00F2FE]/40 to-[#00F2FE] rounded-t-lg transition-all duration-300 hover:to-[#A78BFA]"
                  style={{ height: `${h}%` }}
                />
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-[#94A3B8] pt-2">
            <Clock className="w-3.5 h-3.5 text-[#00F2FE]" />
            <span>Última sincronización sin interrupciones</span>
          </div>
        </div>
      ),
    },
    {
      id: "card-2",
      title: "Gestor de Tareas de Diseño",
      tag: "Flujo Minimalista",
      tagColor: "bg-[#F43F5E]/10 text-[#F43F5E] border-[#F43F5E]/30",
      rotation: "lg:rotate-0 lg:-translate-y-4",
      borderGlow: "hover:border-[#F43F5E]/40",
      shadow: "hover:shadow-[0_20px_50px_-10px_rgba(244,63,94,0.25)]",
      content: (
        <div className="space-y-3.5 text-left">
          <div className="flex items-center justify-between pb-3 border-b border-white/8">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-[#F43F5E]" />
              <span className="text-xs font-bold text-[#F8FAFC]">Hoy • 3 prioridades</span>
            </div>
            <span className="text-xs font-semibold text-[#94A3B8]">12:30 PM</span>
          </div>

          <div className="space-y-2">
            <div className="p-3 bg-[#090B10]/80 rounded-xl border border-white/8 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-4 h-4 rounded-full border-2 border-[#00F2FE] bg-[#00F2FE]/20" />
                <span className="text-xs font-bold text-[#F8FAFC]">
                  Revisión tipográfica Geist
                </span>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#34D399]/15 text-[#34D399]">
                Completado
              </span>
            </div>

            <div className="p-3 bg-[#090B10]/80 rounded-xl border border-white/8 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-4 h-4 rounded-full border-2 border-[#F43F5E]" />
                <span className="text-xs font-bold text-[#F8FAFC]">
                  Test de contraste OLED AAAA
                </span>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#F43F5E]/15 text-[#F43F5E]">
                En progreso
              </span>
            </div>

            <div className="p-3 bg-[#090B10]/80 rounded-xl border border-white/8 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-4 h-4 rounded-full border-2 border-[#A78BFA]" />
                <span className="text-xs font-bold text-[#F8FAFC]">
                  Tokens Tailwind v4
                </span>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#A78BFA]/15 text-[#CEBDFF]">
                16:00
              </span>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: "card-3",
      title: "Biblioteca de Componentes",
      tag: "Tokens Lumina",
      tagColor: "bg-[#A78BFA]/10 text-[#CEBDFF] border-[#A78BFA]/30",
      rotation: "lg:rotate-2",
      borderGlow: "hover:border-[#A78BFA]/40",
      shadow: "hover:shadow-[0_20px_50px_-10px_rgba(167,139,250,0.25)]",
      content: (
        <div className="space-y-3.5 text-left">
          <div className="flex items-center justify-between pb-3 border-b border-white/8">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-[#A78BFA]" />
              <span className="text-xs font-bold text-[#F8FAFC]">Controles reactivos</span>
            </div>
            <span className="text-xs font-bold text-[#A78BFA]">v3.2</span>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between p-2.5 bg-[#090B10]/80 rounded-xl border border-white/8">
              <span className="text-xs font-semibold text-[#F8FAFC]">Modo Obsidian</span>
              <button
                onClick={() => setToggleActive(!toggleActive)}
                className={`w-10 h-6 rounded-full p-1 flex items-center transition-colors cursor-pointer ${
                  toggleActive ? "bg-[#00F2FE] justify-end" : "bg-[#1E2438] justify-start"
                }`}
              >
                <div className="w-4 h-4 bg-[#090B10] rounded-full shadow-xs" />
              </button>
            </div>

            <div className="flex items-center justify-between p-2.5 bg-[#090B10]/80 rounded-xl border border-white/8">
              <span className="text-xs font-semibold text-[#F8FAFC]">Aura Especular</span>
              <div className="w-24 h-2 bg-[#1E2438] rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#00F2FE] to-[#A78BFA] rounded-full transition-all"
                  style={{ width: `${sliderVal}%` }}
                />
              </div>
            </div>

            <div className="p-3 bg-[#090B10]/80 rounded-xl border border-white/8 flex items-center justify-between">
              <span className="text-xs font-bold text-[#F8FAFC]">Botón Primario</span>
              <button className="px-3.5 py-1 bg-gradient-to-r from-[#00F2FE] to-[#A78BFA] text-[#090B10] text-xs font-bold rounded-lg shadow-[0_0_12px_rgba(0,242,254,0.35)]">
                Acción
              </button>
            </div>
          </div>
        </div>
      ),
    },
  ];

  return (
    <section id="showcase" className="py-24 relative overflow-hidden">
      {/* Background radial glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[500px] bg-[#A78BFA]/10 rounded-full blur-[130px] pointer-events-none -z-10" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        {/* Header */}
        <div className="max-w-3xl mx-auto space-y-4 mb-16">
          <div className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full bg-[#151A28] border border-white/10 text-xs font-bold uppercase tracking-wider text-[#CEBDFF]">
            <Layers className="w-3.5 h-3.5 text-[#00F2FE]" />
            <span>Showcase Interactivo OLED</span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#F8FAFC] tracking-tight">
            Una interfaz diseñada para habitar
          </h2>
          <p className="text-base sm:text-lg text-[#94A3B8]">
            Observa cómo cada módulo convive en perfecta armonía gracias a una
            perspectiva tridimensional suave, contraste absoluto y specular glow.
          </p>
        </div>

        {/* 3 Floating 3D Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-center max-w-6xl mx-auto">
          {showcaseCards.map((card, idx) => (
            <motion.div
              key={card.id}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: idx * 0.15 }}
              whileHover={{ scale: 1.02, rotate: 0 }}
              className={`rounded-2xl sm:rounded-3xl p-6 sm:p-7 bg-[#151A28]/85 border border-white/10 backdrop-blur-2xl transition-all duration-300 shadow-[0_20px_50px_-15px_rgba(0,0,0,0.9)] ${card.rotation} ${card.borderGlow} ${card.shadow}`}
            >
              <div className="flex items-center justify-between mb-5">
                <span
                  className={`text-[11px] font-bold px-3 py-1 rounded-full border ${card.tagColor}`}
                >
                  {card.tag}
                </span>
                <span className="w-2 h-2 rounded-full bg-white/20" />
              </div>
              <h3 className="text-lg font-bold text-[#F8FAFC] mb-4 text-left">
                {card.title}
              </h3>
              {card.content}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
