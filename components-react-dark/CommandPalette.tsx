"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  X,
  Palette,
  Terminal,
  Layers,
  Sparkles,
  Sun,
  Moon,
  Copy,
  Check,
  ArrowRight,
} from "lucide-react";
import { useTheme } from "@/context/ThemeContext";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const { theme, toggleTheme } = useTheme();
  const [query, setQuery] = useState("");
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (isOpen) {
          onClose();
        } else {
          // Open handled by parent or state
        }
      }
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const copyToClipboard = (hex: string) => {
    navigator.clipboard.writeText(hex);
    setCopiedToken(hex);
    setTimeout(() => setCopiedToken(null), 1800);
  };

  const tokenList = [
    { name: "Cyan Eléctrico", hex: "#00F2FE", desc: "Acento primario & halo glow" },
    { name: "Lila Luminoso", hex: "#A78BFA", desc: "Acento secundario & tool nodes" },
    { name: "Menta Suave", hex: "#34D399", desc: "Estado activo & 60 FPS feedback" },
    { name: "Coral Vibrante", hex: "#F43F5E", desc: "Alertas críticas & ventana mac" },
    { name: "Obsidian Void", hex: "#090B10", desc: "Lienzo base OLED absoluto" },
  ];

  const quickActions = [
    {
      title: "Ir a Estudio Interactivo",
      href: "#estudio",
      icon: Terminal,
      color: "text-[#00F2FE]",
    },
    {
      title: "Explorar Arquitectura Sensorial",
      href: "#caracteristicas",
      icon: Layers,
      color: "text-[#A78BFA]",
    },
    {
      title: "Ver Showcase & Proyectos",
      href: "#showcase",
      icon: Sparkles,
      color: "text-[#34D399]",
    },
    {
      title: theme === "dark" ? "Cambiar a Modo Pastel Serenidad" : "Cambiar a Modo Obsidian Lumina",
      action: toggleTheme,
      icon: theme === "dark" ? Sun : Moon,
      color: "text-[#FBBF24]",
    },
  ];

  const filteredTokens = tokenList.filter(
    (t) =>
      t.name.toLowerCase().includes(query.toLowerCase()) ||
      t.hex.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 sm:px-6">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/75 backdrop-blur-md"
          />

          {/* Palette Dialog */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ duration: 0.2 }}
            className="relative w-full max-w-xl rounded-2xl bg-[#0F121C] border border-white/10 shadow-[0_25px_60px_-15px_rgba(0,0,0,0.9)] overflow-hidden z-10"
          >
            {/* Search Input bar */}
            <div className="flex items-center px-4 py-3.5 border-b border-white/10 gap-3">
              <Search className="w-5 h-5 text-[#94A3B8]" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Buscar componente, token o acción... (ej: Cyan, #00F2FE, Estudio)"
                className="w-full bg-transparent text-sm sm:text-base text-white placeholder-[#64748B] focus:outline-none"
                autoFocus
              />
              <button
                onClick={onClose}
                className="p-1 rounded-lg hover:bg-white/10 text-[#94A3B8] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Content Body */}
            <div className="max-h-[60vh] overflow-y-auto p-4 space-y-4">
              {/* Quick Actions */}
              <div>
                <span className="text-[11px] font-semibold tracking-wider uppercase text-[#64748B] px-2 block mb-2">
                  Acciones Rápidas
                </span>
                <div className="space-y-1">
                  {quickActions.map((act, i) => {
                    const Icon = act.icon;
                    return (
                      <button
                        key={i}
                        onClick={() => {
                          if (act.action) {
                            act.action();
                          } else if (act.href) {
                            window.location.hash = act.href;
                          }
                          onClose();
                        }}
                        className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/5 border border-transparent hover:border-white/10 text-left transition-all group"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center">
                            <Icon className={`w-4 h-4 ${act.color}`} />
                          </div>
                          <span className="text-sm font-medium text-[#E2E2E9] group-hover:text-white">
                            {act.title}
                          </span>
                        </div>
                        <ArrowRight className="w-4 h-4 text-[#64748B] group-hover:text-[#00F2FE] group-hover:translate-x-0.5 transition-all" />
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Tokens Palette from Stitch */}
              <div>
                <span className="text-[11px] font-semibold tracking-wider uppercase text-[#64748B] px-2 block mb-2">
                  Tokens de Color (Stitch Obsidian Lumina)
                </span>
                <div className="space-y-1.5">
                  {filteredTokens.map((t) => (
                    <div
                      key={t.hex}
                      className="flex items-center justify-between px-3 py-2 rounded-xl bg-[#151A28]/80 border border-white/5 hover:border-white/15 transition-all"
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className="w-7 h-7 rounded-lg border border-white/20 shadow-sm"
                          style={{ backgroundColor: t.hex }}
                        />
                        <div>
                          <div className="text-xs font-semibold text-white">
                            {t.name}
                          </div>
                          <div className="text-[11px] text-[#94A3B8]">
                            {t.desc}
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => copyToClipboard(t.hex)}
                        className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-mono text-[#00F2FE] border border-white/10 transition-colors"
                      >
                        {copiedToken === t.hex ? (
                          <>
                            <Check className="w-3 h-3 text-[#34D399]" />
                            <span className="text-[#34D399]">Copiado</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3" />
                            <span>{t.hex}</span>
                          </>
                        )}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="px-4 py-2.5 bg-[#090B10] border-t border-white/10 flex items-center justify-between text-[11px] text-[#64748B]">
              <span>Presiona <strong>ESC</strong> para salir</span>
              <span>Stitch MCP • Obsidian Lumina Theme</span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
