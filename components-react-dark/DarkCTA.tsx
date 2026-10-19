"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Lock, Mail, ArrowRight, CheckCircle2, Sparkles, Key } from "lucide-react";

export function DarkCTA() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) {
      setSubmitted(true);
    }
  };

  return (
    <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 mb-24">
      <div className="relative rounded-2xl sm:rounded-3xl overflow-hidden p-8 sm:p-14 bg-gradient-to-b from-[#181D2E] to-[#0D101A] border border-white/10 shadow-[0_25px_60px_-15px_rgba(0,0,0,0.9)]">
        {/* Glow Backdrops inside CTA */}
        <div className="absolute -top-24 -right-24 w-80 h-80 bg-[#00F2FE]/15 rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-80 h-80 bg-[#A78BFA]/15 rounded-full blur-[100px] pointer-events-none" />

        <div className="relative z-10 max-w-2xl mx-auto text-center">
          {/* Pill Tag */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/5 border border-white/10 mb-5">
            <Lock className="w-3.5 h-3.5 text-[#00F2FE]" />
            <span className="text-xs font-semibold text-[#E2E2E9]">
              Acceso Anticipado Cerrado
            </span>
          </div>

          {/* Headline */}
          <h2 className="text-3xl sm:text-5xl font-bold text-[#F8FAFC] tracking-tight mb-4">
            Eleva tu diseño al plano de la serenidad visual
          </h2>

          {/* Subtitle */}
          <p className="text-base sm:text-lg text-[#94A3B8] mb-8 leading-relaxed font-normal">
            Únete a más de 12,000 arquitectos de interfaces en nuestro canal privado y
            recibe las plantillas maestras antes del lanzamiento público general.
          </p>

          {/* Interactive Form */}
          <AnimatePresence mode="wait">
            {!submitted ? (
              <motion.form
                key="form"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onSubmit={handleSubmit}
                className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto"
              >
                <div className="relative flex-grow">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#94A3B8] w-4 h-4" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="tu.nombre@estudio.design"
                    required
                    className="w-full pl-10 pr-4 py-3.5 rounded-xl bg-[#090B10]/80 border border-white/15 text-[#F8FAFC] placeholder-[#64748B] text-sm focus:outline-none focus:border-[#00F2FE] focus:ring-1 focus:ring-[#00F2FE] transition-all"
                  />
                </div>
                <button
                  type="submit"
                  className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-[#00F2FE] to-[#A78BFA] text-[#090B10] text-sm font-bold tracking-wide glow-cyan-hover shadow-[0_0_20px_rgba(0,242,254,0.35)] transition-all whitespace-nowrap active:scale-98 cursor-pointer flex items-center justify-center gap-2"
                >
                  <Key className="w-4 h-4 text-[#090B10]" />
                  <span>Solicitar Llave</span>
                </button>
              </motion.form>
            ) : (
              <motion.div
                key="success"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="p-5 rounded-2xl bg-[#00F2FE]/10 border border-[#00F2FE]/30 max-w-md mx-auto flex items-center gap-3.5 text-left"
              >
                <div className="w-10 h-10 rounded-xl bg-[#00F2FE]/20 flex items-center justify-center flex-shrink-0">
                  <CheckCircle2 className="w-5 h-5 text-[#00F2FE]" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">
                    ¡Solicitud de llave registrada!
                  </h4>
                  <p className="text-xs text-[#94A3B8]">
                    Hemos enviado tu pase confidencial a <span className="text-[#00F2FE] font-mono">{email}</span>.
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <p className="text-xs text-[#64748B] mt-5">
            Sin spam. Cifrado de extremo a extremo. Cancela tu suscripción en cualquier instante.
          </p>
        </div>
      </div>
    </section>
  );
}
