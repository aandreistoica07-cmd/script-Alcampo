"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  ArrowRight,
  Sun,
  Moon,
  Menu,
  X,
  Sparkles,
} from "lucide-react";
import { useTheme } from "@/context/ThemeContext";
import { CommandPalette } from "./CommandPalette";

export function DarkNavbar() {
  const { theme, toggleTheme } = useTheme();
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <>
      <header
        className={`fixed top-4 left-1/2 -translate-x-1/2 w-[calc(100%-2rem)] max-w-6xl rounded-2xl z-40 transition-all duration-300 ${
          isScrolled
            ? "bg-[#0F121C]/85 backdrop-blur-2xl border border-white/12 shadow-[0_20px_50px_rgba(0,0,0,0.8)] py-2.5 px-4 sm:px-6"
            : "bg-[#0F121C]/65 backdrop-blur-xl border border-white/8 shadow-2xl shadow-black/40 py-3.5 px-4 sm:px-6"
        }`}
      >
        <div className="flex justify-between items-center w-full">
          {/* Logo & Dark Edition Status Pill */}
          <div className="flex items-center gap-3">
            <a href="#" className="flex items-center gap-2.5 group">
              <div className="relative w-8 h-8 rounded-xl bg-[#1A1B21] border border-white/15 flex items-center justify-center overflow-hidden transition-transform group-hover:scale-105">
                <div className="absolute inset-0 bg-[#00F2FE]/20 blur-sm" />
                <span className="w-2.5 h-2.5 rounded-full bg-[#00F2FE] shadow-[0_0_10px_#00F2FE]" />
              </div>
              <span className="text-xl font-bold tracking-tight text-[#F8FAFC]">
                Serena
              </span>
            </a>

            {/* Dark Edition Status Pill */}
            <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-full bg-[#1E1F25]/80 border border-white/10">
              <span className="w-1.5 h-1.5 rounded-full bg-[#CEBDFF] shadow-[0_0_8px_#CEBDFF]" />
              <span className="text-[11px] font-semibold text-[#CEBDFF] tracking-wide uppercase">
                Dark Edition
              </span>
            </div>
          </div>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center gap-1 bg-[#090B10]/70 p-1 rounded-xl border border-white/8">
            <a
              href="#caracteristicas"
              className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-[#00F2FE] hover:text-white hover:bg-white/5 transition-all"
            >
              Características
            </a>
            <a
              href="#estudio"
              className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-[#94A3B8] hover:text-white hover:bg-white/5 transition-all"
            >
              Espacio Creativo
            </a>
            <a
              href="#showcase"
              className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-[#94A3B8] hover:text-white hover:bg-white/5 transition-all"
            >
              Showcase
            </a>
            <a
              href="#metricas"
              className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-[#94A3B8] hover:text-white hover:bg-white/5 transition-all"
            >
              Métricas
            </a>
            <a
              href="#precios"
              className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-[#94A3B8] hover:text-white hover:bg-white/5 transition-all"
            >
              Precios
            </a>
          </nav>

          {/* Trailing Actions: Search capsule, Theme toggle, CTA */}
          <div className="flex items-center gap-2 sm:gap-2.5">
            {/* Search capsule (Cmd+K) */}
            <button
              onClick={() => setPaletteOpen(true)}
              className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#090B10]/80 border border-white/10 text-xs text-[#94A3B8] hover:text-white hover:border-white/20 transition-all cursor-pointer group"
              title="Buscar tokens y componentes (⌘K)"
            >
              <Search className="w-3.5 h-3.5 group-hover:text-[#00F2FE] transition-colors" />
              <span className="font-mono text-[11px] bg-white/10 px-1.5 py-0.5 rounded text-[#E2E2E9]">
                ⌘K
              </span>
            </button>

            {/* Theme Toggle Button (Dark Obsidian vs Light Pastel) */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-xl bg-[#1A1B21] border border-white/10 text-[#CEBDFF] hover:text-[#00F2FE] hover:border-white/20 transition-all cursor-pointer"
              title={theme === "dark" ? "Cambiar a Modo Pastel" : "Cambiar a Modo Oscuro Obsidian"}
            >
              {theme === "dark" ? (
                <Sun className="w-4 h-4 text-[#FBBF24]" />
              ) : (
                <Moon className="w-4 h-4 text-[#A78BFA]" />
              )}
            </button>

            {/* Primary Glowing Gradient Button */}
            <a
              href="#estudio"
              className="relative group overflow-hidden px-4 sm:px-5 py-2 rounded-xl bg-gradient-to-r from-[#00F2FE] to-[#A78BFA] text-[#090B10] text-xs sm:text-sm font-bold tracking-wide shadow-[0_0_20px_rgba(0,242,254,0.35)] hover:shadow-[0_0_30px_rgba(0,242,254,0.6)] active:scale-[0.98] transition-all duration-200 flex items-center gap-1.5"
            >
              <span className="relative z-10 flex items-center gap-1.5 font-semibold">
                <span>Comenzar Proyecto</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
              </span>
            </a>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-xl bg-[#1A1B21] border border-white/10 text-[#E2E2E9] hover:text-white"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Menu */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="md:hidden border-t border-white/10 mt-3 pt-3 space-y-2"
            >
              <div className="flex flex-col space-y-1">
                <a
                  href="#caracteristicas"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-3 py-2 rounded-lg text-sm font-medium text-[#00F2FE] hover:bg-white/5"
                >
                  Características
                </a>
                <a
                  href="#estudio"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-3 py-2 rounded-lg text-sm font-medium text-[#E2E2E9] hover:bg-white/5"
                >
                  Espacio Creativo Live
                </a>
                <a
                  href="#showcase"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-3 py-2 rounded-lg text-sm font-medium text-[#E2E2E9] hover:bg-white/5"
                >
                  Showcase
                </a>
                <a
                  href="#metricas"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-3 py-2 rounded-lg text-sm font-medium text-[#E2E2E9] hover:bg-white/5"
                >
                  Métricas OLED
                </a>
                <a
                  href="#precios"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-3 py-2 rounded-lg text-sm font-medium text-[#E2E2E9] hover:bg-white/5"
                >
                  Precios
                </a>
              </div>
              <div className="pt-2 border-t border-white/10 flex items-center justify-between">
                <button
                  onClick={() => {
                    setPaletteOpen(true);
                    setMobileMenuOpen(false);
                  }}
                  className="flex items-center gap-2 text-xs text-[#00F2FE]"
                >
                  <Search className="w-3.5 h-3.5" />
                  <span>Abrir buscador (⌘K)</span>
                </button>
                <button
                  onClick={toggleTheme}
                  className="flex items-center gap-1.5 text-xs text-[#CEBDFF]"
                >
                  {theme === "dark" ? <Sun className="w-3.5 h-3.5 text-[#FBBF24]" /> : <Moon className="w-3.5 h-3.5" />}
                  <span>{theme === "dark" ? "Modo Pastel" : "Modo Oscuro"}</span>
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </header>

      {/* Command Palette Modal */}
      <CommandPalette isOpen={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </>
  );
}
