"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  Touchpad,
  SunMoon,
  RefreshCw,
  ChevronRight,
  Zap,
  CheckCircle2,
  Copy,
  Check,
} from "lucide-react";

export function DarkFeatures() {
  const [copiedSync, setCopiedSync] = useState(false);
  const [activeCard, setActiveCard] = useState<number | null>(null);

  const handleCopyCode = () => {
    navigator.clipboard.writeText(
      `import { useObsidianTheme } from '@serena/lumina';\nconst { tokens } = useObsidianTheme();`
    );
    setCopiedSync(true);
    setTimeout(() => setCopiedSync(false), 2000);
  };

  const features = [
    {
      id: 1,
      tag: "Física Natural",
      title: "Micro-interacciones Táctiles",
      desc: "Frecuencia de respuesta háptica inmediata y transiciones elásticas calibradas a nivel milisegundo para un control cinestésico absoluto en la composición de capas.",
      linkText: "Explorar motor háptico",
      icon: Touchpad,
      accentColor: "#00F2FE",
      borderColor: "hover:border-[#00F2FE]/40",
      glowColor: "rgba(0, 242, 254, 0.25)",
      badgeBg: "bg-[#00F2FE]/10 text-[#00F2FE] border-[#00F2FE]/30",
    },
    {
      id: 2,
      tag: "Color AAAA",
      title: "Contraste OLED Certificado",
      desc: "Negros puros (#000000 / #090B10) sin efecto halo blooming, ahorro de batería hasta un 34% en pantallas ProMotion y confort visual para largas jornadas creativas.",
      linkText: "Certificaciones OLED",
      icon: SunMoon,
      accentColor: "#A78BFA",
      borderColor: "hover:border-[#A78BFA]/40",
      glowColor: "rgba(167, 139, 250, 0.25)",
      badgeBg: "bg-[#A78BFA]/10 text-[#CEBDFF] border-[#A78BFA]/30",
    },
    {
      id: 3,
      tag: "Sync Instantáneo",
      title: "Tokens Multiplataforma",
      desc: "Exportación instantánea a CSS Variables, Tailwind v4, React, SwiftUI y Figma Variables con sincronización bidireccional continua en tiempo real.",
      linkText: "SDKs soportados",
      icon: RefreshCw,
      accentColor: "#34D399",
      borderColor: "hover:border-[#34D399]/40",
      glowColor: "rgba(52, 211, 153, 0.25)",
      badgeBg: "bg-[#34D399]/10 text-[#34D399] border-[#34D399]/30",
    },
  ];

  return (
    <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mb-24" id="caracteristicas">
      {/* Section Header */}
      <div className="text-center max-w-3xl mx-auto mb-16">
        <span className="text-xs sm:text-sm font-bold text-[#00F2FE] tracking-wider uppercase bg-[#00F2FE]/10 px-3.5 py-1.5 rounded-full border border-[#00F2FE]/20 inline-block mb-3">
          Arquitectura Sensorial
        </span>
        <h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-[#F8FAFC] mt-2 mb-4">
          Ingeniería de software para la contemplación creativa
        </h2>
        <p className="text-base sm:text-lg text-[#94A3B8] leading-relaxed">
          Cada interacción responde a leyes físicas naturales, protegiendo tu concentración nocturna con contraste sin concesiones.
        </p>
      </div>

      {/* 3-Column Glass Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
        {features.map((f, i) => {
          const Icon = f.icon;
          return (
            <motion.div
              key={f.id}
              initial={{ opacity: 0, y: 25 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.45, delay: i * 0.1 }}
              whileHover={{ y: -4 }}
              onHoverStart={() => setActiveCard(f.id)}
              onHoverEnd={() => setActiveCard(null)}
              className={`rounded-2xl sm:rounded-3xl p-6 sm:p-8 bg-[#151A28]/60 border border-white/8 backdrop-blur-xl transition-all duration-300 relative group flex flex-col justify-between ${f.borderColor}`}
              style={{
                boxShadow:
                  activeCard === f.id
                    ? `0 20px 45px -10px rgba(0,0,0,0.8), 0 0 30px ${f.glowColor}`
                    : "0 10px 30px -10px rgba(0,0,0,0.5)",
              }}
            >
              <div>
                {/* Icon in glowing border box */}
                <div
                  className="w-12 h-12 rounded-2xl flex items-center justify-center mb-6 border transition-all duration-300"
                  style={{
                    backgroundColor: `${f.accentColor}15`,
                    borderColor: `${f.accentColor}40`,
                    boxShadow: `0 0 16px ${f.accentColor}25`,
                  }}
                >
                  <Icon className="w-6 h-6" style={{ color: f.accentColor }} />
                </div>

                {/* Pill Tag */}
                <span
                  className={`px-3 py-1 rounded-full text-[11px] font-bold border inline-block mb-3.5 ${f.badgeBg}`}
                >
                  {f.tag}
                </span>

                {/* Card Title */}
                <h3 className="text-xl font-bold text-[#F8FAFC] mb-3 group-hover:text-white transition-colors">
                  {f.title}
                </h3>

                {/* Card Body */}
                <p className="text-sm text-[#94A3B8] leading-relaxed mb-6 font-normal">
                  {f.desc}
                </p>
              </div>

              {/* Bottom Interactive Link */}
              <div className="pt-4 border-t border-white/8 flex items-center justify-between">
                <span
                  className="flex items-center text-xs font-bold transition-transform group-hover:translate-x-1 cursor-pointer"
                  style={{ color: f.accentColor }}
                >
                  <span>{f.linkText}</span>
                  <ChevronRight className="w-4 h-4 ml-1" />
                </span>

                {f.id === 3 && (
                  <button
                    onClick={handleCopyCode}
                    className="flex items-center gap-1 text-[11px] font-mono text-[#94A3B8] hover:text-white bg-white/5 hover:bg-white/10 px-2.5 py-1 rounded-lg border border-white/10 transition-colors cursor-pointer"
                    title="Copiar snippet de integración React"
                  >
                    {copiedSync ? (
                      <>
                        <Check className="w-3 h-3 text-[#34D399]" />
                        <span className="text-[#34D399]">Copiado</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Snippet</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
