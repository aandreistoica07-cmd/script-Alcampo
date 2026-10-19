"use client";

import React from "react";
import { ArrowUp, Sparkles } from "lucide-react";

export function DarkFooter() {
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <footer className="bg-[#090B10] border-t border-white/8 transition-colors duration-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 flex flex-col md:flex-row justify-between items-center gap-6 w-full">
        {/* Brand & Copyright */}
        <div className="flex flex-col sm:flex-row items-center gap-4 text-center sm:text-left">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#00F2FE] shadow-[0_0_8px_#00F2FE]" />
            <span className="text-lg font-bold text-[#F8FAFC] tracking-tight">
              Serena
            </span>
          </div>
          <span className="hidden sm:inline text-white/20">•</span>
          <span className="text-xs text-[#94A3B8]">
            © 2025 Serena Studio Inc. Crafted for deep creative focus.
          </span>
        </div>

        {/* Links & Operational Status Pill */}
        <div className="flex flex-wrap items-center justify-center gap-5 sm:gap-6">
          <a
            href="#caracteristicas"
            className="text-xs text-[#94A3B8] hover:text-[#00F2FE] transition-colors"
          >
            Características
          </a>
          <a
            href="#estudio"
            className="text-xs text-[#94A3B8] hover:text-[#00F2FE] transition-colors"
          >
            Design Tokens
          </a>
          <a
            href="#showcase"
            className="text-xs text-[#94A3B8] hover:text-[#00F2FE] transition-colors"
          >
            Manifesto
          </a>
          <a
            href="#privacidad"
            className="text-xs text-[#94A3B8] hover:text-[#00F2FE] transition-colors"
          >
            Privacidad
          </a>

          {/* Live System Operational Pill */}
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[#151A28] border border-white/10">
            <span className="w-1.5 h-1.5 rounded-full bg-[#34D399] shadow-[0_0_6px_#34D399] animate-pulse" />
            <span className="text-[11px] font-semibold text-[#34D399]">
              Todos los sistemas operativos
            </span>
          </div>

          {/* Scroll to Top */}
          <button
            onClick={scrollToTop}
            className="p-1.5 rounded-lg bg-[#151A28] border border-white/10 text-[#94A3B8] hover:text-white hover:border-white/20 transition-all cursor-pointer"
            title="Volver arriba"
          >
            <ArrowUp className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </footer>
  );
}
