"use client";

import React from "react";
import { motion } from "framer-motion";
import { Sun, Moon, Sparkles } from "lucide-react";
import { useTheme } from "@/context/ThemeContext";

export function FloatingThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <motion.button
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={toggleTheme}
      className={`fixed bottom-6 right-6 z-40 flex items-center gap-2.5 px-4 py-2.5 rounded-full border shadow-2xl backdrop-blur-xl transition-all duration-300 cursor-pointer ${
        theme === "dark"
          ? "bg-[#0F121C]/90 border-white/15 text-[#F8FAFC] shadow-[0_0_25px_rgba(0,242,254,0.25)] hover:border-[#00F2FE]/50"
          : "bg-white/90 border-[#E8E4F0] text-[#2D2A3E] shadow-tint-lilac hover:bg-[#F4F1FF]"
      }`}
      title={theme === "dark" ? "Cambiar a modo pastel serenidad" : "Cambiar a modo oscuro Obsidian Lumina"}
    >
      <div className="relative">
        {theme === "dark" ? (
          <Sun className="w-4 h-4 text-[#FBBF24] transition-transform rotate-0" />
        ) : (
          <Moon className="w-4 h-4 text-[#7C3AED] transition-transform rotate-0" />
        )}
      </div>
      <span className="text-xs font-semibold">
        {theme === "dark" ? "Obsidian Lumina" : "Modo Serenidad"}
      </span>
      <span
        className={`w-2 h-2 rounded-full ${
          theme === "dark"
            ? "bg-[#00F2FE] shadow-[0_0_8px_#00F2FE]"
            : "bg-[#A8DADC] shadow-[0_0_8px_#A8DADC]"
        }`}
      />
    </motion.button>
  );
}
