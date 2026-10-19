"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  Terminal,
  Palette,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Eye,
} from "lucide-react";
import { DarkStudioMockup } from "./DarkStudioMockup";

export function DarkHero() {
  return (
    <section className="relative pt-32 pb-16 overflow-hidden">
      {/* Ambient OLED Light Orbs */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute -top-40 left-1/4 w-[520px] h-[520px] bg-[#00F2FE]/10 rounded-full blur-[140px]" />
        <div className="absolute top-96 -right-20 w-[480px] h-[480px] bg-[#A78BFA]/15 rounded-full blur-[160px]" />
        <div className="absolute bottom-40 left-1/3 w-[600px] h-[600px] bg-[#34D399]/5 rounded-full blur-[180px]" />
        <div className="absolute inset-0 bg-grid-pattern opacity-40" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center pt-6 pb-12">
        {/* Live Release Tag */}
        <motion.div
          initial={{ opacity: 0, y: -15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-[#1A1B21]/80 border border-white/12 shadow-inner mb-6 backdrop-blur-md"
        >
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00F2FE] opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00F2FE]" />
          </span>
          <span className="text-xs font-semibold text-[#E2E2E9] tracking-wider">
            Serena v3.2 • Edición Dark Mode
          </span>
          <span className="text-[10px] font-bold bg-[#A78BFA]/20 text-[#CEBDFF] px-2 py-0.5 rounded-full border border-[#A78BFA]/30">
            Obsidian Lumina
          </span>
        </motion.div>

        {/* Hero Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-[#F8FAFC] max-w-4xl mx-auto leading-[1.08] mb-6"
        >
          Diseño que respira. Interfaces que{" "}
          <span className="relative inline-block text-transparent bg-clip-text bg-gradient-to-r from-[#00F2FE] via-[#38BDF8] to-[#A78BFA] drop-shadow-[0_0_35px_rgba(0,242,254,0.35)]">
            hipnotizan.
          </span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-base sm:text-xl text-[#94A3B8] max-w-2xl mx-auto mb-10 leading-relaxed font-normal"
        >
          La plataforma de diseño y espacio digital de trabajo optimizada para paneles
          OLED, diseñada para eliminar la fatiga cognitiva y amplificar el estado de
          flujo creativo a 60 FPS.
        </motion.p>

        {/* Hero CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-14"
        >
          <a
            href="#estudio"
            className="w-full sm:w-auto px-7 py-3.5 rounded-xl bg-gradient-to-r from-[#00F2FE] to-[#A78BFA] text-[#090B10] text-sm sm:text-base font-bold tracking-wide flex items-center justify-center gap-2.5 glow-cyan-hover shadow-[0_0_20px_rgba(0,242,254,0.35)] transition-all duration-200 active:scale-98"
          >
            <Terminal className="w-4 h-4 text-[#090B10]" />
            <span>Explorar Estudio Live</span>
          </a>

          <a
            href="#caracteristicas"
            className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-[#1A1B21]/70 hover:bg-[#1E2438] border border-white/12 hover:border-white/25 text-[#F8FAFC] text-sm sm:text-base font-semibold flex items-center justify-center gap-2.5 transition-all duration-150"
          >
            <Palette className="w-4 h-4 text-[#A78BFA]" />
            <span>Ver Documentación &amp; Tokens</span>
          </a>
        </motion.div>

        {/* Stats Ticker */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="inline-grid grid-cols-1 sm:grid-cols-3 gap-6 sm:gap-12 px-8 py-3.5 rounded-2xl bg-[#0F121C]/70 border border-white/10 backdrop-blur-md shadow-xl mb-12"
        >
          <div className="flex items-center gap-3 justify-center">
            <span className="w-2.5 h-2.5 rounded-full bg-[#34D399] shadow-[0_0_8px_#34D399]" />
            <span className="text-xl font-bold text-[#F8FAFC]">12,400+</span>
            <span className="text-xs text-[#94A3B8]">Diseñadores activos</span>
          </div>

          <div className="flex items-center gap-3 justify-center border-t sm:border-t-0 sm:border-l border-white/10 pt-3 sm:pt-0 sm:pl-8">
            <span className="w-2.5 h-2.5 rounded-full bg-[#00F2FE] shadow-[0_0_8px_#00F2FE]" />
            <span className="text-xl font-bold text-[#F8FAFC]">0.04ms</span>
            <span className="text-xs text-[#94A3B8]">Latencia de render</span>
          </div>

          <div className="flex items-center gap-3 justify-center border-t sm:border-t-0 sm:border-l border-white/10 pt-3 sm:pt-0 sm:pl-8">
            <span className="w-2.5 h-2.5 rounded-full bg-[#A78BFA] shadow-[0_0_8px_#A78BFA]" />
            <span className="text-xl font-bold text-[#F8FAFC]">OLED Contrast</span>
            <span className="text-xs text-[#94A3B8]">AAAA Studio</span>
          </div>
        </motion.div>
      </div>

      {/* Embedded Studio Mockup Centerpiece */}
      <DarkStudioMockup />
    </section>
  );
}
